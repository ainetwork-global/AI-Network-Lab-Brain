from __future__ import annotations

import csv
import math
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "04_OPPORTUNITIES" / "LIVE_TRUTH_EXECUTION_QUEUE.csv"
PLATFORMS = ROOT / "04_OPPORTUNITIES" / "participant_platform_status.csv"
OUTPUT = ROOT / "04_OPPORTUNITIES" / "GLOBAL_DECISION_QUEUE.csv"
REPORT = ROOT / "12_REPORTS" / "LATEST_GLOBAL_ECONOMIC_DECISIONS.md"

UNKNOWN_PAYMENT = {"", "unknown", "not informed", "not_informed", "none"}


def number(value: object, default: float = 0.0) -> float:
    try:
        return float(str(value or "").replace(",", ""))
    except ValueError:
        return default


def integer(value: object) -> int:
    return int(number(value))


def evaluate(row: dict[str, str]) -> dict[str, str]:
    status = str(row.get("truth_status") or "")
    url = str(row.get("url") or "")
    payment = str(row.get("payment_method") or "").strip()
    source_validation = str(row.get("source_validation") or "")
    reward_basis = str(row.get("reward_basis") or "")
    comments = integer(row.get("comments"))
    competing_prs = integer(row.get("open_competing_prs"))
    hours = max(1.0, number(row.get("estimated_hours"), 40.0))
    reward = max(0.0, number(row.get("reward_amount")))

    blocked = status.startswith("BLOCKED_") or status in {
        "STALE_LOCKED_CONFIRMATION_REQUIRED", "REMOVED_FROM_LIVE_QUEUE"
    }
    review = status.endswith("REVIEW_REQUIRED") and not blocked
    ready = status == "READY_FOR_TECHNICAL_REVIEW"
    github_task = "github.com/" in url and "/issues/" in url
    payment_known = payment.lower() not in UNKNOWN_PAYMENT
    official = source_validation == "official_adapter"

    if blocked:
        route = "ARCHIVE_BLOCKED"
        next_action = "Não investir tempo; manter apenas no histórico."
    elif ready and github_task and payment_known and competing_prs == 0 and comments < 8:
        route = "AUTONOMOUS_TECHNICAL_EXECUTION"
        next_action = "Preparar solução e testes no workspace; ação externa continua sujeita a aprovação."
    elif review:
        route = "HUMAN_DECISION_REQUIRED"
        next_action = "Destacar no dashboard com motivo, evidências e decisão solicitada."
    else:
        route = "EVIDENCE_REFRESH_REQUIRED"
        next_action = "Atualizar evidências de abertura, pagamento, elegibilidade e concorrência."

    truth_points = 40 if ready else 18 if review else 0
    payment_points = 18 if payment_known else 0
    payment_points += 7 if official else 0
    competition_points = 20 if competing_prs == 0 and comments < 8 else 8 if competing_prs < 3 and comments < 25 else 0
    effort_points = max(0.0, 15.0 - math.log2(hours) * 2.0)
    score = max(0.0, min(100.0, truth_points + payment_points + competition_points + effort_points))

    probability = 0.0
    if ready:
        probability = 0.32
    elif review:
        probability = 0.10
    if official:
        probability += 0.08
    if not payment_known:
        probability *= 0.35
    if competing_prs:
        probability /= 1 + competing_prs
    if comments >= 8:
        probability *= 0.55
    if blocked:
        probability = 0.0
    if reward_basis in {"maximum_advertised_reward", "accepted_submission_not_guaranteed"}:
        probability *= 0.65
    probability = max(0.0, min(0.55, probability))
    expected_value = reward * probability
    expected_hourly = expected_value / hours

    result = dict(row)
    result.update({
        "decision_route": route,
        "economic_score": f"{score:.2f}",
        "estimated_payment_probability": f"{probability:.4f}",
        "risk_adjusted_value": f"{expected_value:.2f}",
        "risk_adjusted_hourly_value": f"{expected_hourly:.2f}",
        "automation_eligible": str(route == "AUTONOMOUS_TECHNICAL_EXECUTION").lower(),
        "external_action_allowed": "false",
        "decision_next_action": next_action,
        "decision_generated_at": datetime.now(timezone.utc).isoformat(),
    })
    return result


def read(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    rows = [evaluate(row) for row in read(INPUT)]
    route_order = {
        "AUTONOMOUS_TECHNICAL_EXECUTION": 0,
        "HUMAN_DECISION_REQUIRED": 1,
        "EVIDENCE_REFRESH_REQUIRED": 2,
        "ARCHIVE_BLOCKED": 3,
    }
    rows.sort(key=lambda row: (
        route_order.get(row["decision_route"], 9),
        -number(row["economic_score"]),
        -number(row["risk_adjusted_hourly_value"]),
    ))
    for rank, row in enumerate(rows, 1):
        row["decision_rank"] = str(rank)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = [
        "decision_rank", "decision_route", "economic_score",
        "estimated_payment_probability", "risk_adjusted_value",
        "risk_adjusted_hourly_value", "automation_eligible",
        "external_action_allowed", "decision_next_action",
        "decision_generated_at",
    ]
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    counts = {route: sum(row["decision_route"] == route for row in rows) for route in route_order}
    platforms = read(PLATFORMS)
    lines = [
        "# GLOBAL ECONOMIC DECISION ENGINE", "",
        f"Generated: `{datetime.now(timezone.utc).isoformat()}`", "",
        f"- Automatic technical execution: **{counts['AUTONOMOUS_TECHNICAL_EXECUTION']}**",
        f"- Human decision required: **{counts['HUMAN_DECISION_REQUIRED']}**",
        f"- Evidence refresh required: **{counts['EVIDENCE_REFRESH_REQUIRED']}**",
        f"- Archived/blocked: **{counts['ARCHIVE_BLOCKED']}**",
        f"- Participant platforms monitored: **{len(platforms)}**",
        "- External claims, applications, submissions, signatures, KYC and money movement performed: **0**",
        "", "## Highest-priority decisions", "",
        "| Rank | Route | Opportunity | Score | Risk-adjusted value | Next action |",
        "|---:|---|---|---:|---:|---|",
    ]
    for row in rows[:20]:
        lines.append(
            f"| {row['decision_rank']} | {row['decision_route']} | {row.get('title', '')} | "
            f"{row['economic_score']} | {row.get('reward_currency', '')} {row['risk_adjusted_value']} | "
            f"{row['decision_next_action']} |"
        )
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("; ".join(f"{key}={value}" for key, value in counts.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
