from __future__ import annotations

import csv
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "11_DATA" / "global_revenue_brain.db"
CSV_PATH = ROOT / "04_OPPORTUNITIES" / "VERIFIED_EXECUTION_QUEUE.csv"
REPORT_PATH = ROOT / "12_REPORTS" / "LATEST_VERIFIED_EXECUTION_QUEUE.md"
TARGET_PATH = ROOT / "00_CURRENT_STATE" / "CURRENT_BEST_TARGET.md"

FIELDS = [
    "rank",
    "queue_status",
    "verification_score",
    "priority_score",
    "title",
    "category",
    "source",
    "url",
    "reward_amount",
    "reward_currency",
    "payment_method",
    "difficulty",
    "estimated_hours",
    "risk_level",
    "country_eligibility",
    "country_restrictions",
    "kyc_required",
    "human_approval_required",
    "verification_status",
    "recommended_action",
    "recommendation_reason",
    "verified_at",
]

GLOBAL_TERMS = (
    "worldwide",
    "global",
    "any country",
    "all countries",
    "open to all",
    "brazil",
    "brasil",
)

RESTRICTED_TERMS = (
    "us residents only",
    "u.s. residents only",
    "united states only",
    "residents of the united states",
    "citizens of the united states",
    "eu residents only",
    "european union only",
)


def text(value: object) -> str:
    return str(value or "").strip()


def number(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def country_eligibility(restrictions: object) -> str:
    value = text(restrictions).lower()
    if not value:
        return "UNKNOWN_REVIEW_REQUIRED"
    if any(term in value for term in RESTRICTED_TERMS):
        return "BRAZIL_NOT_ELIGIBLE"
    if any(term in value for term in GLOBAL_TERMS):
        return "BRAZIL_LIKELY_ELIGIBLE"
    return "UNKNOWN_REVIEW_REQUIRED"


def queue_status(row: sqlite3.Row, eligibility: str) -> str:
    if not row["link_active"]:
        return "BLOCKED_LINK_INACTIVE"
    if not row["executable"]:
        return "BLOCKED_NOT_EXECUTABLE"
    if not row["explicit_reward"] or number(row["reward_amount"]) <= 0:
        return "BLOCKED_REWARD_UNVERIFIED"
    if row["capital_required"]:
        return "BLOCKED_INITIAL_COST"
    if text(row["risk_level"]).lower() not in {"baixo", "médio", "medio"}:
        return "BLOCKED_RISK"
    if text(row["verification_status"]).lower() in {"rejected", "expired"}:
        return "BLOCKED_REJECTED_OR_EXPIRED"
    if eligibility == "BRAZIL_NOT_ELIGIBLE":
        return "BLOCKED_COUNTRY"
    if row["kyc_required"]:
        return "IDENTITY_REVIEW_REQUIRED"
    if eligibility == "UNKNOWN_REVIEW_REQUIRED":
        return "ELIGIBILITY_REVIEW_REQUIRED"
    if not text(row["payment_method"]):
        return "PAYMENT_ROUTE_REVIEW_REQUIRED"
    return "READY_FOR_TECHNICAL_REVIEW"


def priority_score(row: sqlite3.Row, status: str) -> float:
    score = number(row["verification_score"])
    score += min(number(row["reward_amount"]) / 1000.0, 10.0)
    if text(row["risk_level"]).lower() == "baixo":
        score += 8.0
    if text(row["payment_method"]):
        score += 5.0
    if status == "READY_FOR_TECHNICAL_REVIEW":
        score += 12.0
    elif status.endswith("REVIEW_REQUIRED"):
        score -= 5.0
    else:
        score -= 50.0
    return round(max(0.0, min(100.0, score)), 2)


def main() -> int:
    generated_at = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(DATABASE) as database:
        database.row_factory = sqlite3.Row
        rows = database.execute(
            """
            SELECT
                v.*,
                COALESCE(o.status, '') AS opportunity_status
            FROM opportunity_verifications v
            LEFT JOIN opportunities o
              ON CAST(o.id AS TEXT) = CAST(v.opportunity_id AS TEXT)
            ORDER BY v.verification_score DESC, v.verified_at DESC
            """
        ).fetchall()

    queue: list[dict[str, object]] = []

    for row in rows:
        eligibility = country_eligibility(row["country_restrictions"])
        status = queue_status(row, eligibility)
        queue.append(
            {
                "rank": 0,
                "queue_status": status,
                "verification_score": number(row["verification_score"]),
                "priority_score": priority_score(row, status),
                "title": text(row["title"]),
                "category": text(row["category"]),
                "source": text(row["source"]),
                "url": text(row["url"]),
                "reward_amount": number(row["reward_amount"]),
                "reward_currency": text(row["reward_currency"]),
                "payment_method": text(row["payment_method"]),
                "difficulty": text(row["difficulty"]),
                "estimated_hours": number(row["estimated_hours"]),
                "risk_level": text(row["risk_level"]),
                "country_eligibility": eligibility,
                "country_restrictions": text(row["country_restrictions"]),
                "kyc_required": int(bool(row["kyc_required"])),
                "human_approval_required": int(bool(row["human_approval_required"])),
                "verification_status": text(row["verification_status"]),
                "recommended_action": text(row["recommended_action"]),
                "recommendation_reason": text(row["recommendation_reason"]),
                "verified_at": text(row["verified_at"]),
            }
        )

    status_order = {
        "READY_FOR_TECHNICAL_REVIEW": 0,
        "PAYMENT_ROUTE_REVIEW_REQUIRED": 1,
        "ELIGIBILITY_REVIEW_REQUIRED": 2,
        "IDENTITY_REVIEW_REQUIRED": 3,
    }
    queue.sort(
        key=lambda item: (
            status_order.get(text(item["queue_status"]), 9),
            -number(item["priority_score"]),
            -number(item["reward_amount"]),
        )
    )

    for rank, item in enumerate(queue, 1):
        item["rank"] = rank

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(queue)

    actionable = [
        item for item in queue
        if item["queue_status"] == "READY_FOR_TECHNICAL_REVIEW"
    ]
    review = [
        item for item in queue
        if text(item["queue_status"]).endswith("REVIEW_REQUIRED")
    ]
    blocked = len(queue) - len(actionable) - len(review)

    lines = [
        "# VERIFIED EXECUTION QUEUE",
        "",
        f"Generated at: `{generated_at}`",
        "",
        f"- Verified records: **{len(queue)}**",
        f"- Ready for technical review: **{len(actionable)}**",
        f"- Human review required: **{len(review)}**",
        f"- Blocked: **{blocked}**",
        "",
        "No claim, submission, contract acceptance, wallet signature, or financial transaction was performed.",
        "",
        "## Top candidates",
        "",
    ]

    for item in queue[:25]:
        lines.extend(
            [
                f"### {item['rank']}. {item['title']}",
                "",
                f"- Queue status: `{item['queue_status']}`",
                f"- Priority score: `{item['priority_score']}`",
                f"- Verification score: `{item['verification_score']}`",
                f"- Reward: `{item['reward_currency']} {item['reward_amount']}`",
                f"- Payment method: `{item['payment_method'] or 'unknown'}`",
                f"- Brazil eligibility: `{item['country_eligibility']}`",
                f"- Risk: `{item['risk_level']}`",
                f"- URL: {item['url']}",
                "",
            ]
        )

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    best = actionable[0] if actionable else (review[0] if review else None)
    if best:
        target_lines = [
            "# Current Best Target",
            "",
            f"Status: `{best['queue_status']}`",
            "",
            f"Title: {best['title']}",
            f"Reward: {best['reward_currency']} {best['reward_amount']}",
            f"Priority score: {best['priority_score']}",
            f"URL: {best['url']}",
            "",
            "External action performed: `false`",
        ]
    else:
        target_lines = [
            "# Current Best Target",
            "",
            "Status: `NO_PAYMENT_VERIFIED_CANDIDATE`",
            "",
            "Nenhuma oportunidade atingiu o limiar mínimo de confiança.",
        ]
    TARGET_PATH.write_text("\n".join(target_lines) + "\n", encoding="utf-8")

    print(f"Verified records: {len(queue)}")
    print(f"Ready for technical review: {len(actionable)}")
    print(f"Human review required: {len(review)}")
    print(f"Blocked: {blocked}")
    print(f"Queue: {CSV_PATH}")
    print(f"Report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
