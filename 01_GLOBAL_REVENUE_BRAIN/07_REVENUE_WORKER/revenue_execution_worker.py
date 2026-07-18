import csv
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

KANBAN = (
    ROOT
    / "04_OPPORTUNITIES"
    / "EXECUTION_KANBAN.csv"
)

READY_QUEUE = (
    ROOT
    / "04_OPPORTUNITIES"
    / "EXECUTION_READY_QUEUE.csv"
)

OUTPUT = (
    ROOT
    / "07_REVENUE_WORKER"
    / "NEXT_EXECUTION.md"
)


ACTION_PRIORITY = {
    "execute_now": 0,
    "begin_execution": 0,
    "start_work": 0,
    "ready_to_begin": 0,
    "request_human_approval_to_begin": 1,
    "request_human_approval": 1,
    "human_approval_required": 1,
}

NON_ACTIONABLE_ACTIONS = {
    "",
    "keep_in_observation",
    "observe",
    "observation",
    "wait",
    "monitor",
    "do_not_execute",
    "reject",
    "blocked",
}

STATUS_PRIORITY = {
    "READY_TO_EXECUTE": 0,
    "AWAITING_HUMAN_APPROVAL": 1,
    "HUMAN_REVIEW_REQUIRED": 1,
}

BLOCKED_STATUSES = {
    "INVALID",
    "OBSERVATION",
    "PAID",
    "REJECTED",
    "CANCELLED",
    "COMPLETED",
    "SUBMITTED",
    "BLOCKED",
}


def clean(value):
    return str(value or "").strip()


def number(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def integer(value, default=999999):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def read_csv(path):
    if not path.exists():
        return []

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        return list(csv.DictReader(file))


def first_value(row, fields):
    for field in fields:
        value = clean(row.get(field))

        if value:
            return value

    return ""


def normalized_action(row):
    return first_value(
        row,
        [
            "recommended_action",
            "recommendation",
            "next_action",
            "execution_recommendation",
        ],
    ).lower()


def normalized_status(row):
    return first_value(
        row,
        [
            "execution_status",
            "status",
            "queue_status",
            "live_validation_status",
        ],
    ).upper()


def is_actionable(row):
    action = normalized_action(row)
    status = normalized_status(row)

    if status in BLOCKED_STATUSES:
        return False

    if action in NON_ACTIONABLE_ACTIONS:
        return False

    if action in ACTION_PRIORITY:
        return True

    return status in {
        "AWAITING_HUMAN_APPROVAL",
        "HUMAN_REVIEW_REQUIRED",
    }


def candidate_sort_key(row):
    action = normalized_action(row)
    status = normalized_status(row)

    return (
        ACTION_PRIORITY.get(action, 9),
        STATUS_PRIORITY.get(status, 9),
        integer(row.get("rank_position")),
        -number(row.get("final_execution_score")),
        -number(row.get("payment_probability")),
        -number(row.get("reward_amount")),
    )


def markdown_value(value):
    return clean(value).replace("\r", " ").replace("\n", " ")


rows = read_csv(KANBAN)

source_used = KANBAN

if not rows:
    rows = read_csv(READY_QUEUE)
    source_used = READY_QUEUE

actionable_rows = [
    row
    for row in rows
    if is_actionable(row)
]

actionable_rows.sort(key=candidate_sort_key)

OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True,
)

generated_at = datetime.now(timezone.utc).isoformat()

if not actionable_rows:
    observed_rows = [
        row
        for row in rows
        if normalized_action(row)
        == "keep_in_observation"
    ]

    lines = [
        "# NEXT EXECUTION",
        "",
        f"Generated: {generated_at}",
        "",
        "Execution status: NO_ACTIONABLE_CANDIDATE",
        "",
        (
            "Nenhuma oportunidade com ação executável "
            "ou aprovação humana pendente foi encontrada."
        ),
        "",
        (
            "Oportunidades mantidas em observação: "
            f"{len(observed_rows)}"
        ),
        "",
        "Nenhuma tarefa deve ser iniciada automaticamente.",
    ]

    OUTPUT.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    print()
    print("=" * 72)
    print("REVENUE EXECUTION WORKER")
    print("=" * 72)
    print("Actionable candidates: 0")
    print("Observed candidates:", len(observed_rows))
    print("Result: NO_ACTIONABLE_CANDIDATE")
    print("Output:", OUTPUT)

    raise SystemExit(0)


selected = actionable_rows[0]

organization = first_value(
    selected,
    [
        "organization",
        "owner",
        "github_owner",
    ],
)

repository = first_value(
    selected,
    [
        "repository",
        "repository_name",
        "repo",
    ],
)

if "/" in repository and not organization:
    organization, repository = repository.split("/", 1)

issue_number = first_value(
    selected,
    [
        "issue_number",
        "number",
        "issue",
    ],
)

title = first_value(
    selected,
    [
        "task_title",
        "title",
        "opportunity_title",
        "name",
    ],
)

url = first_value(
    selected,
    [
        "url",
        "issue_url",
        "source_url",
    ],
)

reward = first_value(
    selected,
    [
        "reward",
        "reward_amount",
        "expected_cash_value",
    ],
)

reward_currency = first_value(
    selected,
    [
        "reward_currency",
        "currency",
    ],
)

payment_probability = first_value(
    selected,
    [
        "payment_probability",
        "payment_probability_percent",
    ],
)

final_score = first_value(
    selected,
    [
        "final_execution_score",
        "execution_score",
    ],
)

recommended_action = normalized_action(selected)
execution_status = normalized_status(selected)

if recommended_action in {
    "request_human_approval_to_begin",
    "request_human_approval",
    "human_approval_required",
}:
    worker_decision = "AWAITING_HUMAN_APPROVAL"
else:
    worker_decision = "READY_TO_BEGIN"

lines = [
    "# NEXT EXECUTION",
    "",
    f"Generated: {generated_at}",
    "",
    f"Worker decision: {worker_decision}",
    f"Execution status: {execution_status}",
    f"Recommended action: {recommended_action}",
    "",
    "## Opportunity",
    "",
    f"Organization: {markdown_value(organization)}",
    f"Repository: {markdown_value(repository)}",
    f"Issue: {markdown_value(issue_number)}",
    f"Title: {markdown_value(title)}",
    "",
    f"Reward: {markdown_value(reward_currency)} {markdown_value(reward)}",
    f"Payment probability: {markdown_value(payment_probability)}",
    f"Final execution score: {markdown_value(final_score)}",
    "",
    f"URL: {markdown_value(url)}",
    "",
    "## Checklist obrigatório antes da execução",
    "",
    "[ ] Abrir a documentação e a issue original",
    "[ ] Confirmar que a oportunidade continua aberta",
    "[ ] Confirmar que a recompensa continua válida",
    "[ ] Confirmar regras para reivindicar ou reservar a tarefa",
    "[ ] Verificar se já existe outro executor trabalhando nela",
    "[ ] Solicitar aprovação humana quando necessário",
    "[ ] Preparar o ambiente local do repositório",
    "[ ] Reproduzir tecnicamente o problema",
    "[ ] Definir o plano mínimo de implementação",
    "[ ] Produzir os entregáveis",
    "[ ] Executar testes",
    "[ ] Revisar tecnicamente",
    "[ ] Submeter manualmente",
    "[ ] Registrar o resultado e eventual pagamento",
    "",
    "## Routing",
    "",
    (
        "Oportunidades com recommended_action="
        "keep_in_observation são excluídas da próxima execução."
    ),
    "",
    f"Source queue: {source_used.name}",
]

OUTPUT.write_text(
    "\n".join(lines) + "\n",
    encoding="utf-8",
)

print()
print("=" * 72)
print("REVENUE EXECUTION WORKER")
print("=" * 72)
print("Candidates analyzed:", len(rows))
print("Actionable candidates:", len(actionable_rows))
print("Selected organization:", organization)
print("Selected repository:", repository)
print("Selected issue:", issue_number)
print("Execution status:", execution_status)
print("Recommended action:", recommended_action)
print("Worker decision:", worker_decision)
print("Payment probability:", payment_probability)
print("Final execution score:", final_score)
print("URL:", url)
print("Output:", OUTPUT)
