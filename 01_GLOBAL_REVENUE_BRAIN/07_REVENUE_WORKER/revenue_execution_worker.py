import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

KANBAN = ROOT / "06_OPERATIONS" / "EXECUTION_KANBAN.csv"
OUTPUT = ROOT / "07_REVENUE_WORKER" / "NEXT_EXECUTION.md"

rows = []

if KANBAN.exists():
    with KANBAN.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

def number(value, default=0.0):
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default

def rank(value):
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return 999999

eligible = [
    row for row in rows
    if (row.get("status") or "").strip() not in {
        "PAID",
        "REJECTED",
        "CANCELLED",
        "COMPLETED",
        "SUBMITTED",
    }
]

eligible.sort(
    key=lambda row: (
        0 if str(row.get("is_current_best_target", "")).strip() == "1" else 1,
        rank(row.get("rank_position")),
        -number(row.get("final_execution_score")),
    )
)

selected = eligible[0] if eligible else None

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

if selected:
    content = f"""# NEXT EXECUTION

Status:
{selected.get("status", "")}

Source:
{selected.get("source", "")}

Title:
{selected.get("title", "")}

Organization:
{selected.get("organization", "")}

Repository:
{selected.get("repository", "")}

Issue:
{selected.get("issue_number", "")}

Reward:
{selected.get("reward", "")}

Payment probability:
{selected.get("payment_probability", "")}%

Final execution score:
{selected.get("final_execution_score", "")}

Recommended action:
{selected.get("recommended_action", "")}

URL:
{selected.get("url", "")}

## Checklist obrigatório antes da execução

[ ] Abrir a documentação e a issue original
[ ] Confirmar que a oportunidade continua aberta
[ ] Confirmar que a recompensa continua válida
[ ] Confirmar regras para reivindicar ou reservar a tarefa
[ ] Verificar se já existe outro executor trabalhando nela
[ ] Solicitar aprovação humana para começar
[ ] Produzir os entregáveis
[ ] Revisar tecnicamente
[ ] Submeter manualmente
[ ] Registrar o resultado e eventual pagamento
"""
else:
    content = """# NEXT EXECUTION

Nenhuma oportunidade elegível encontrada.
"""

with OUTPUT.open("w", encoding="utf-8-sig", newline="") as file:
    file.write(content)

print()
print("=" * 70)
print("REVENUE WORKER")
print("=" * 70)
print("Worker generated:")
print(OUTPUT)

if selected:
    print()
    print("Selecionado:")
    print(selected.get("title", ""))
    print(selected.get("reward", ""))
    print(selected.get("status", ""))
