import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

RANKING_INPUT = (
    ROOT
    / "04_OPPORTUNITIES"
    / "execution_candidate_ranking.csv"
)

LIVE_INPUT = (
    ROOT
    / "04_OPPORTUNITIES"
    / "live_validated_opportunities.csv"
)

OUTPUT = (
    ROOT
    / "04_OPPORTUNITIES"
    / "EXECUTION_READY_QUEUE.csv"
)

FIELDS = [
    "task_id",
    "source",
    "task_title",
    "reward",
    "url",
    "execution_status",
    "rank_position",
    "is_current_best_target",
    "reward_currency",
    "reward_amount",
    "payment_probability",
    "expected_cash_value",
    "estimated_hours",
    "probability_adjusted_value_per_hour",
    "planning_status",
    "readiness_score",
    "cash_conversion_speed",
    "execution_risk",
    "final_execution_score",
    "recommended_action",
    "organization",
    "repository",
    "issue_number",
    "live_validation_status",
    "live_validation_score",
    "live_validation_reason",
    "github_state",
    "reward_mentioned_live",
    "assignee_count",
    "claim_signal",
    "completion_signal",
    "validated_at",
]

STATUS_PRIORITY = {
    "READY_TO_EXECUTE": 0,
    "HUMAN_REVIEW_REQUIRED": 1,
    "AWAITING_HUMAN_APPROVAL": 2,
    "OBSERVATION": 3,
    "INVALID": 9,
}


def text(value):
    return str(value or "").strip()


def number(value, default=0.0):
    try:
        return float(text(value))
    except (TypeError, ValueError):
        return default


def integer(value, default=999999):
    try:
        return int(float(text(value)))
    except (TypeError, ValueError):
        return default


def issue_key(repository, issue_number):
    return (
        text(repository).lower(),
        text(issue_number),
    )


if not RANKING_INPUT.exists():
    raise FileNotFoundError(
        f"Ranking não encontrado: {RANKING_INPUT}"
    )

if not LIVE_INPUT.exists():
    raise FileNotFoundError(
        f"Validação ao vivo não encontrada: {LIVE_INPUT}"
    )

with RANKING_INPUT.open(
    "r",
    encoding="utf-8-sig",
    newline="",
) as file:
    ranking_rows = list(csv.DictReader(file))

with LIVE_INPUT.open(
    "r",
    encoding="utf-8-sig",
    newline="",
) as file:
    live_rows = list(csv.DictReader(file))

live_index = {
    issue_key(
        row.get("repository"),
        row.get("issue_number"),
    ): row
    for row in live_rows
}

queue = []

for index, candidate in enumerate(ranking_rows, 1):
    key = issue_key(
        candidate.get("repository"),
        candidate.get("issue_number"),
    )

    live = live_index.get(key, {})

    live_status = text(
        live.get("live_validation_status")
    )

    recommended_action = text(
        candidate.get("recommended_action")
    )

    if live_status == "READY_TO_EXECUTE":
        execution_status = "READY_TO_EXECUTE"

    elif live_status == "INVALID":
        execution_status = "INVALID"

    elif live_status == "HUMAN_REVIEW_REQUIRED":
        execution_status = "HUMAN_REVIEW_REQUIRED"

    elif recommended_action == "request_human_approval_to_begin":
        execution_status = "AWAITING_HUMAN_APPROVAL"

    else:
        execution_status = "OBSERVATION"

    currency = text(candidate.get("reward_currency"))
    reward_amount = number(candidate.get("reward_amount"))

    if currency and reward_amount:
        reward = f"{currency} {reward_amount:.2f}"
    else:
        reward = ""

    queue.append({
        "task_id": index,
        "source": "Economic Ranking + Live Validation",
        "task_title": candidate.get("title", ""),
        "reward": reward,
        "url": candidate.get("source_url", ""),
        "execution_status": execution_status,
        "rank_position": candidate.get("rank_position", ""),
        "is_current_best_target": candidate.get(
            "is_current_best_target",
            "",
        ),
        "reward_currency": currency,
        "reward_amount": candidate.get("reward_amount", ""),
        "payment_probability": candidate.get(
            "payment_probability",
            "",
        ),
        "expected_cash_value": candidate.get(
            "expected_cash_value",
            "",
        ),
        "estimated_hours": candidate.get(
            "estimated_hours",
            "",
        ),
        "probability_adjusted_value_per_hour": candidate.get(
            "probability_adjusted_value_per_hour",
            "",
        ),
        "planning_status": candidate.get(
            "planning_status",
            "",
        ),
        "readiness_score": candidate.get(
            "readiness_score",
            "",
        ),
        "cash_conversion_speed": candidate.get(
            "cash_conversion_speed",
            "",
        ),
        "execution_risk": candidate.get(
            "execution_risk",
            "",
        ),
        "final_execution_score": candidate.get(
            "final_execution_score",
            "",
        ),
        "recommended_action": recommended_action,
        "organization": candidate.get("organization", ""),
        "repository": candidate.get("repository", ""),
        "issue_number": candidate.get("issue_number", ""),
        "live_validation_status": live_status,
        "live_validation_score": live.get(
            "live_validation_score",
            "",
        ),
        "live_validation_reason": live.get(
            "validation_reason",
            "",
        ),
        "github_state": live.get("github_state", ""),
        "reward_mentioned_live": live.get(
            "reward_mentioned_live",
            "",
        ),
        "assignee_count": live.get("assignee_count", ""),
        "claim_signal": live.get("claim_signal", ""),
        "completion_signal": live.get(
            "completion_signal",
            "",
        ),
        "validated_at": live.get("validated_at", ""),
    })

queue.sort(
    key=lambda row: (
        STATUS_PRIORITY.get(
            row["execution_status"],
            8,
        ),
        -number(row["final_execution_score"]),
        integer(row["rank_position"]),
    )
)

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

with OUTPUT.open(
    "w",
    encoding="utf-8-sig",
    newline="",
) as file:
    writer = csv.DictWriter(
        file,
        fieldnames=FIELDS,
    )
    writer.writeheader()
    writer.writerows(queue)

print()
print("=" * 70)
print("EXECUTION READY QUEUE COM VALIDAÇÃO AO VIVO")
print("=" * 70)
print("Candidatos:", len(queue))
print("Output:", OUTPUT)

if queue:
    first = queue[0]

    print()
    print("Melhor alvo executável:")
    print("Título:", first["task_title"])
    print("Status:", first["execution_status"])
    print("Recompensa:", first["reward"])
    print(
        "Score econômico:",
        first["final_execution_score"],
    )
    print(
        "Score ao vivo:",
        first["live_validation_score"],
    )
