from __future__ import annotations

import csv
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "04_OPPORTUNITIES" / "GLOBAL_DECISION_QUEUE.csv"
OUTPUT = ROOT / "04_OPPORTUNITIES" / "FAST_LANE_QUEUE.csv"
REPORT = ROOT / "12_REPORTS" / "LATEST_FAST_LANE.md"
DB = ROOT / "11_DATA" / "global_revenue_brain.db"

BLOCKED = {"ARCHIVE_BLOCKED", "EVIDENCE_REFRESH_REQUIRED"}
SLOW_OR_SPECULATIVE_CATEGORIES = {"authorized_bug_bounty", "hackathon", "competition"}


def number(value: object, default: float = 0.0) -> float:
    try:
        return float(str(value or "").replace(",", ""))
    except ValueError:
        return default


def source_memory() -> dict[str, tuple[int, int, float]]:
    if not DB.exists():
        return {}
    with sqlite3.connect(DB) as db:
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "revenue_execution_history" not in tables:
            return {}
        rows = db.execute(
            """SELECT COALESCE(source, ''),
                      SUM(CASE WHEN execution_result = 'success' THEN 1 ELSE 0 END),
                      SUM(CASE WHEN execution_result <> 'success' THEN 1 ELSE 0 END),
                      COALESCE(SUM(actual_revenue), 0)
               FROM revenue_execution_history GROUP BY COALESCE(source, '')"""
        ).fetchall()
    return {str(source).lower(): (int(wins), int(losses), float(revenue)) for source, wins, losses, revenue in rows}


def evaluate(row: dict[str, str], memory: dict[str, tuple[int, int, float]]) -> dict[str, str] | None:
    route = row.get("decision_route", "")
    reward = number(row.get("reward_amount"))
    if route in BLOCKED or reward <= 0:
        return None
    hours = max(0.25, number(row.get("estimated_hours"), 8.0))
    category = row.get("category", "").strip().lower()
    reward_basis = row.get("reward_basis", "").strip().lower()
    eligibility = row.get("eligibility_status", "").strip().lower()
    if (
        hours > 8.0
        or category in SLOW_OR_SPECULATIVE_CATEGORIES
        or reward_basis in {"maximum_advertised_reward", "accepted_submission_not_guaranteed"}
        or eligibility == "specialist_only"
    ):
        return None
    base_probability = number(row.get("estimated_payment_probability"))
    source = row.get("source", "").strip().lower()
    wins, losses, realized = memory.get(source, (0, 0, 0.0))
    learned_probability = (wins + 1.0) / (wins + losses + 2.0)
    evidence_weight = min(0.50, (wins + losses) / 10.0)
    probability = base_probability * (1.0 - evidence_weight) + learned_probability * evidence_weight
    expected_value = reward * probability
    expected_hourly = expected_value / hours
    quick_bonus = 1.0 / math.sqrt(hours)
    realized_bonus = min(2.0, math.log1p(realized) / 5.0)
    fast_score = expected_hourly * quick_bonus * (1.0 + realized_bonus)
    result = dict(row)
    result.update({
        "fast_lane_score": f"{fast_score:.6f}",
        "learned_payment_probability": f"{probability:.4f}",
        "expected_value_per_hour": f"{expected_hourly:.4f}",
        "historical_successes": str(wins),
        "historical_failures": str(losses),
        "historical_realized_revenue": f"{realized:.2f}",
        "fast_lane_route": (
            "AUTO_PREPARE" if row.get("automation_eligible", "").lower() == "true"
            else "REQUEST_APPROVAL"
        ),
        "fast_lane_generated_at": datetime.now(timezone.utc).isoformat(),
    })
    return result


def main() -> int:
    if not INPUT.exists():
        rows: list[dict[str, str]] = []
    else:
        with INPUT.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
    memory = source_memory()
    ranked = [item for row in rows if (item := evaluate(row, memory)) is not None]
    ranked.sort(key=lambda row: (-number(row["fast_lane_score"]), number(row.get("estimated_hours"), 999999)))
    for index, row in enumerate(ranked, 1):
        row["fast_lane_rank"] = str(index)

    fields = [
        "fast_lane_rank", "fast_lane_route", "fast_lane_score",
        "learned_payment_probability", "expected_value_per_hour",
        "historical_successes", "historical_failures", "historical_realized_revenue",
        "fast_lane_generated_at",
    ]
    for row in ranked:
        for key in row:
            if key not in fields:
                fields.append(key)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(ranked)

    lines = [
        "# FAST LANE", "", f"Generated: `{datetime.now(timezone.utc).isoformat()}`", "",
        f"- Positive, non-blocked opportunities: **{len(ranked)}**", "",
        "| Rank | Route | Opportunity | Reward | Expected/hour | Probability |",
        "|---:|---|---|---:|---:|---:|",
    ]
    for row in ranked[:20]:
        lines.append(
            f"| {row['fast_lane_rank']} | {row['fast_lane_route']} | {row.get('title', '')} | "
            f"{row.get('reward_currency', '')} {row.get('reward_amount', '')} | "
            f"{row['expected_value_per_hour']} | {row['learned_payment_probability']} |"
        )
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Fast lane candidates={len(ranked)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
