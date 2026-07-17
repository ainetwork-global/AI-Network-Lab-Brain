from __future__ import annotations

import csv
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REWARD_FIELDS = [
    "reward",
    "amount",
    "reward_usd",
    "amount_usd",
    "prize",
    "bounty",
    "budget",
    "value",
    "estimated_value",
]

PAYMENT_PROBABILITY_FIELDS = [
    "payment_probability",
    "payment_prob",
    "payment_score",
]

EXECUTION_PROBABILITY_FIELDS = [
    "execution_probability",
    "execution_prob",
    "feasibility_score",
]

ELIGIBILITY_PROBABILITY_FIELDS = [
    "eligibility_probability",
    "eligibility_score",
]

RECEIPT_PROBABILITY_FIELDS = [
    "receipt_probability",
    "receivability_score",
]

EFFORT_HOURS_FIELDS = [
    "estimated_hours",
    "effort_hours",
    "estimated_time_hours",
    "hours",
]

TITLE_FIELDS = [
    "title",
    "name",
    "opportunity",
    "task",
    "summary",
]

SOURCE_FIELDS = [
    "source",
    "source_name",
    "platform",
]

URL_FIELDS = [
    "url",
    "link",
    "source_url",
]

CURRENCY_FIELDS = [
    "currency",
    "reward_currency",
]

PAYMENT_TYPE_FIELDS = [
    "payment_type",
    "reward_type",
]

HUMAN_ACTION_FIELDS = [
    "requires_human_action",
    "human_review_required",
]

EXCLUDED_NAME_FRAGMENTS = [
    "execution_queue",
    "any_value_execution_queue",
    "adapter_candidate_queue",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def first_value(row: dict[str, Any], fields: list[str]) -> str:
    lower_map = {
        str(key).strip().lower(): value
        for key, value in row.items()
    }

    for field in fields:
        value = lower_map.get(field.lower())

        if value not in (None, ""):
            return text(value)

    return ""


def parse_float(value: Any) -> float | None:
    raw = text(value)

    if not raw:
        return None

    normalized = raw.replace(" ", "")

    if "," in normalized and "." in normalized:
        if normalized.rfind(",") > normalized.rfind("."):
            normalized = normalized.replace(".", "")
            normalized = normalized.replace(",", ".")
        else:
            normalized = normalized.replace(",", "")
    elif "," in normalized:
        normalized = normalized.replace(",", ".")

    match = re.search(r"-?\d+(?:\.\d+)?", normalized)

    if not match:
        return None

    try:
        number = float(match.group(0))
    except ValueError:
        return None

    if math.isnan(number) or math.isinf(number):
        return None

    return number


def normalize_probability(
    value: Any,
    default: float,
) -> float:
    parsed = parse_float(value)

    if parsed is None:
        return default

    if parsed <= 1:
        parsed *= 100

    return max(0.0, min(100.0, parsed))


def normalize_bool(value: Any, default: bool = True) -> bool:
    raw = text(value).lower()

    if raw in {"true", "1", "yes", "sim", "required"}:
        return True

    if raw in {"false", "0", "no", "nao", "não"}:
        return False

    return default


def infer_reward(row: dict[str, Any]) -> float:
    for field in REWARD_FIELDS:
        value = first_value(row, [field])
        parsed = parse_float(value)

        if parsed is not None and parsed >= 0:
            return parsed

    return 0.0


def infer_effort_hours(row: dict[str, Any]) -> float:
    for field in EFFORT_HOURS_FIELDS:
        parsed = parse_float(first_value(row, [field]))

        if parsed is not None and parsed > 0:
            return parsed

    effort = first_value(
        row,
        [
            "estimated_effort",
            "effort",
            "complexity",
        ],
    ).lower()

    mapping = {
        "tiny": 0.25,
        "micro": 0.5,
        "very_low": 0.75,
        "low": 2.0,
        "medium": 8.0,
        "high": 24.0,
        "very_high": 60.0,
    }

    return mapping.get(effort, 4.0)


def process_row(
    row: dict[str, Any],
    source_file: Path,
    row_number: int,
) -> dict[str, Any]:
    reward = infer_reward(row)

    payment_probability = normalize_probability(
        first_value(row, PAYMENT_PROBABILITY_FIELDS),
        60.0,
    )

    execution_probability = normalize_probability(
        first_value(row, EXECUTION_PROBABILITY_FIELDS),
        55.0,
    )

    eligibility_probability = normalize_probability(
        first_value(row, ELIGIBILITY_PROBABILITY_FIELDS),
        70.0,
    )

    receipt_probability = normalize_probability(
        first_value(row, RECEIPT_PROBABILITY_FIELDS),
        75.0,
    )

    effort_hours = infer_effort_hours(row)

    probability_product = (
        payment_probability
        * execution_probability
        * eligibility_probability
        * receipt_probability
    ) / 100_000_000.0

    expected_receivable_value = reward * probability_product

    revenue_velocity = (
        expected_receivable_value / effort_hours
        if effort_hours > 0
        else expected_receivable_value
    )

    title = first_value(row, TITLE_FIELDS)

    if not title:
        title = f"Opportunity row {row_number}"

    source = first_value(row, SOURCE_FIELDS)

    if not source:
        source = source_file.stem

    currency = first_value(row, CURRENCY_FIELDS) or "unknown"

    payment_type = (
        first_value(row, PAYMENT_TYPE_FIELDS)
        or "unknown"
    )

    url = first_value(row, URL_FIELDS)

    requires_human_action = normalize_bool(
        first_value(row, HUMAN_ACTION_FIELDS),
        True,
    )

    direct_executability_score = round(
        (
            execution_probability * 0.35
            + eligibility_probability * 0.25
            + payment_probability * 0.20
            + receipt_probability * 0.20
        ),
        2,
    )

    queue_priority = round(
        revenue_velocity * 100
        + direct_executability_score,
        6,
    )

    return {
        "source_file": str(source_file),
        "source_row": row_number,
        "source": source,
        "title": title,
        "url": url,
        "currency": currency,
        "payment_type": payment_type,
        "reward": round(reward, 8),
        "estimated_hours": round(effort_hours, 4),
        "payment_probability": round(payment_probability, 2),
        "execution_probability": round(execution_probability, 2),
        "eligibility_probability": round(
            eligibility_probability,
            2,
        ),
        "receipt_probability": round(
            receipt_probability,
            2,
        ),
        "expected_receivable_value": round(
            expected_receivable_value,
            8,
        ),
        "revenue_velocity": round(revenue_velocity, 8),
        "direct_executability_score": (
            direct_executability_score
        ),
        "queue_priority": queue_priority,
        "requires_human_action": requires_human_action,
        "status": "pending_human_review",
        "generated_at": utc_now(),
    }


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "Usage: build_any_value_execution_queue.py "
            "<global_brain_path>",
            file=sys.stderr,
        )
        return 2

    global_brain = Path(sys.argv[1]).resolve()
    opportunity_dir = global_brain / "04_OPPORTUNITIES"

    output_csv = (
        opportunity_dir
        / "any_value_execution_queue.csv"
    )

    output_json = (
        global_brain
        / "00_CURRENT_STATE"
        / "ANY_VALUE_EXECUTION_QUEUE_STATE.json"
    )

    report_path = (
        global_brain
        / "12_REPORTS"
        / "LATEST_ANY_VALUE_EXECUTION_QUEUE.md"
    )

    candidates: list[dict[str, Any]] = []

    for csv_path in sorted(
        opportunity_dir.glob("*.csv")
    ):
        lower_name = csv_path.name.lower()

        if any(
            fragment in lower_name
            for fragment in EXCLUDED_NAME_FRAGMENTS
        ):
            continue

        try:
            with csv_path.open(
                "r",
                encoding="utf-8-sig",
                newline="",
            ) as handle:
                reader = csv.DictReader(handle)

                if not reader.fieldnames:
                    continue

                for row_number, row in enumerate(
                    reader,
                    start=2,
                ):
                    if not any(
                        text(value)
                        for value in row.values()
                    ):
                        continue

                    candidate = process_row(
                        row,
                        csv_path,
                        row_number,
                    )

                    candidates.append(candidate)

        except Exception as error:
            print(
                f"Skipping {csv_path}: "
                f"{type(error).__name__}: {error}",
                file=sys.stderr,
            )

    candidates.sort(
        key=lambda item: (
            -float(item["queue_priority"]),
            -float(item["receipt_probability"]),
            -float(item["execution_probability"]),
            float(item["estimated_hours"]),
        )
    )

    for rank, candidate in enumerate(
        candidates,
        start=1,
    ):
        candidate["rank"] = rank

    output_csv.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "rank",
        "source",
        "title",
        "reward",
        "currency",
        "payment_type",
        "estimated_hours",
        "payment_probability",
        "execution_probability",
        "eligibility_probability",
        "receipt_probability",
        "expected_receivable_value",
        "revenue_velocity",
        "direct_executability_score",
        "queue_priority",
        "requires_human_action",
        "status",
        "url",
        "source_file",
        "source_row",
        "generated_at",
    ]

    with output_csv.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )
        writer.writeheader()

        for candidate in candidates:
            writer.writerow(
                {
                    field: candidate.get(field, "")
                    for field in fieldnames
                }
            )

    positive_reward = [
        item
        for item in candidates
        if float(item["reward"]) > 0
    ]

    micro_reward = [
        item
        for item in positive_reward
        if 0 < float(item["reward"]) <= 5
    ]

    state = {
        "generated_at": utc_now(),
        "policy": "any_value_executable_revenue",
        "minimum_reward": 0,
        "total_candidates": len(candidates),
        "positive_reward_candidates": len(
            positive_reward
        ),
        "micro_reward_candidates": len(
            micro_reward
        ),
        "top_candidate": (
            candidates[0]
            if candidates
            else None
        ),
        "external_action_performed": False,
        "application_submitted": False,
        "proposal_submitted": False,
        "task_accepted": False,
        "payment_requested": False,
        "output_csv": str(output_csv),
    }

    output_json.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_json.write_text(
        json.dumps(
            state,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    lines = [
        "# Latest Any-Value Execution Queue",
        "",
        f"Generated at: `{state['generated_at']}`",
        "",
        "## Result",
        "",
        f"- Total candidates: **{len(candidates)}**",
        (
            "- Candidates with explicit positive reward: "
            f"**{len(positive_reward)}**"
        ),
        (
            "- Micro-reward candidates up to 5 units: "
            f"**{len(micro_reward)}**"
        ),
        "- Minimum accepted reward: **none**",
        "",
        "## Highest-ranked candidates",
        "",
        "| Rank | Source | Title | Reward | Currency | Hours | Receipt % | Execution % | Velocity |",
        "|---:|---|---|---:|---|---:|---:|---:|---:|",
    ]

    for item in candidates[:25]:
        safe_title = str(item["title"]).replace(
            "|",
            "/",
        )

        lines.append(
            "| {rank} | {source} | {title} | {reward} | "
            "{currency} | {hours} | {receipt} | "
            "{execution} | {velocity} |".format(
                rank=item["rank"],
                source=item["source"],
                title=safe_title[:110],
                reward=item["reward"],
                currency=item["currency"],
                hours=item["estimated_hours"],
                receipt=item["receipt_probability"],
                execution=item["execution_probability"],
                velocity=item["revenue_velocity"],
            )
        )

    lines.extend(
        [
            "",
            "## Decision rule",
            "",
            (
                "Small tasks are valid when they have strong "
                "executability, receivability and low effort."
            ),
            "",
            "## Safety",
            "",
            "- Application submitted: **no**",
            "- Proposal submitted: **no**",
            "- Task accepted: **no**",
            "- External action performed: **no**",
            "",
        ]
    )

    report_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    report_path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    print("===== ANY-VALUE EXECUTION QUEUE =====")
    print(f"Total candidates: {len(candidates)}")
    print(
        "Positive reward candidates: "
        f"{len(positive_reward)}"
    )
    print(
        "Micro-reward candidates: "
        f"{len(micro_reward)}"
    )
    print(f"Queue: {output_csv}")
    print(f"State: {output_json}")
    print(f"Report: {report_path}")

    print("")
    print("===== TOP 15 =====")

    for item in candidates[:15]:
        print(
            f"{item['rank']}. "
            f"{item['source']} | "
            f"{item['title'][:90]} | "
            f"reward={item['reward']} "
            f"{item['currency']} | "
            f"hours={item['estimated_hours']} | "
            f"receipt={item['receipt_probability']} | "
            f"priority={item['queue_priority']}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
