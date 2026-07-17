import csv
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent

INPUT = ROOT / "04_OPPORTUNITIES" / "execution_candidate_ranking.csv"
OUTPUT = ROOT / "04_OPPORTUNITIES" / "EXECUTION_READY_QUEUE.csv"

OUTPUT_FIELDS = [
    "source",
    "platform",
    "task_title",
    "description",
    "url",
    "country",
    "language",
    "currency",
    "payment_type",
    "reward",
    "estimated_hours",
    "required_skills",
    "execution_probability",
    "payment_probability",
    "receipt_probability",
    "competition_score",
    "expected_roi",
    "repeatability",
    "requires_human_action",
    "status",
    "discovered_at",
    "last_checked",
    "payment_verification_score",
    "deliverables",
    "execution_status",
    "rank_position",
    "is_current_best_target",
    "organization",
    "repository",
    "issue_number",
    "reward_amount",
    "expected_cash_value",
    "probability_adjusted_value_per_hour",
    "planning_status",
    "readiness_score",
    "cash_conversion_speed",
    "execution_risk",
    "final_execution_score",
    "recommended_action",
]

def as_float(value, default=0.0):
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default

def as_int(value, default=999999):
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return default

def classify_deliverables(title):
    text = (title or "").lower()
    deliverables = []

    if any(term in text for term in ("python", "script", "automation")):
        deliverables.append("python_code")

    if any(term in text for term in ("readme", "documentation", "docs")):
        deliverables.append("documentation")

    if any(term in text for term in ("bug", "fix", "issue")):
        deliverables.append("bug_fix")

    if any(term in text for term in ("test", "testing")):
        deliverables.append("tests")

    if any(term in text for term in ("proposal", "agreement", "architecture")):
        deliverables.append("proposal_or_architecture")

    if not deliverables:
        deliverables.append("manual_review")

    return ";".join(deliverables)

if not INPUT.exists():
    raise FileNotFoundError(f"Ranking não encontrado: {INPUT}")

with INPUT.open("r", encoding="utf-8-sig", newline="") as file:
    ranking_rows = list(csv.DictReader(file))

ranking_rows.sort(
    key=lambda row: (
        as_int(row.get("rank_position")),
        -as_float(row.get("final_execution_score")),
    )
)

now = datetime.now(timezone.utc).isoformat()
execution_rows = []

for row in ranking_rows:
    title = (row.get("title") or "").strip()
    currency = (row.get("reward_currency") or "unknown").strip()
    reward_amount = as_float(row.get("reward_amount"))
    payment_probability = as_float(row.get("payment_probability"))
    expected_cash_value = as_float(row.get("expected_cash_value"))
    final_score = as_float(row.get("final_execution_score"))
    recommended_action = (row.get("recommended_action") or "").strip()
    planning_status = (row.get("planning_status") or "").strip()

    reward_text = (
        f"{currency} {reward_amount:.2f}"
        if reward_amount > 0
        else ""
    )

    is_best = str(row.get("is_current_best_target") or "").strip() == "1"

    if is_best:
        execution_status = "AWAITING_HUMAN_APPROVAL"
        status = "CURRENT_BEST_TARGET"
    elif recommended_action == "request_human_approval_to_begin":
        execution_status = "AWAITING_HUMAN_APPROVAL"
        status = "RANKED_CANDIDATE"
    else:
        execution_status = "OBSERVATION"
        status = "RANKED_CANDIDATE"

    description = (
        f"Organization: {row.get('organization', '')}; "
        f"Repository: {row.get('repository', '')}; "
        f"Issue: {row.get('issue_number', '')}; "
        f"Expected cash value: {currency} {expected_cash_value:.2f}; "
        f"Recommended action: {recommended_action}"
    )

    execution_rows.append({
        "source": "Execution Candidate Ranking",
        "platform": "GitHub",
        "task_title": title,
        "description": description,
        "url": row.get("source_url", ""),
        "country": "global",
        "language": "unknown",
        "currency": currency,
        "payment_type": "bounty",
        "reward": reward_text,
        "estimated_hours": row.get("estimated_hours", ""),
        "required_skills": "",
        "execution_probability": "",
        "payment_probability": row.get("payment_probability", ""),
        "receipt_probability": row.get("payment_probability", ""),
        "competition_score": "",
        "expected_roi": row.get("probability_adjusted_value_per_hour", ""),
        "repeatability": "",
        "requires_human_action": "true",
        "status": status,
        "discovered_at": now,
        "last_checked": now,
        "payment_verification_score": round(payment_probability, 2),
        "deliverables": classify_deliverables(title),
        "execution_status": execution_status,
        "rank_position": row.get("rank_position", ""),
        "is_current_best_target": row.get("is_current_best_target", ""),
        "organization": row.get("organization", ""),
        "repository": row.get("repository", ""),
        "issue_number": row.get("issue_number", ""),
        "reward_amount": row.get("reward_amount", ""),
        "expected_cash_value": row.get("expected_cash_value", ""),
        "probability_adjusted_value_per_hour": row.get(
            "probability_adjusted_value_per_hour", ""
        ),
        "planning_status": planning_status,
        "readiness_score": row.get("readiness_score", ""),
        "cash_conversion_speed": row.get("cash_conversion_speed", ""),
        "execution_risk": row.get("execution_risk", ""),
        "final_execution_score": final_score,
        "recommended_action": recommended_action,
    })

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

with OUTPUT.open("w", encoding="utf-8-sig", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=OUTPUT_FIELDS)
    writer.writeheader()
    writer.writerows(execution_rows)

print()
print("=" * 70)
print("EXECUTION READY QUEUE GERADA PELO RANKING")
print("=" * 70)
print("Candidatos:", len(execution_rows))
print("Output:", OUTPUT)

if execution_rows:
    best = execution_rows[0]
    print()
    print("Melhor alvo:")
    print("Título:", best["task_title"])
    print("Recompensa:", best["reward"])
    print("Probabilidade de pagamento:", best["payment_probability"])
    print("Score final:", best["final_execution_score"])
    print("Ação:", best["recommended_action"])
