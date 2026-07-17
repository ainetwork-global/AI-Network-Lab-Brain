import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

INPUT = ROOT / "04_OPPORTUNITIES" / "EXECUTION_READY_QUEUE.csv"
OUTPUT = ROOT / "06_OPERATIONS" / "EXECUTION_KANBAN.csv"

FIELDS = [
    "id",
    "status",
    "source",
    "title",
    "reward",
    "url",
    "complexity",
    "estimated_minutes",
    "submitted_at",
    "paid_at",
    "amount_received",
    "rank_position",
    "is_current_best_target",
    "payment_probability",
    "final_execution_score",
    "recommended_action",
    "organization",
    "repository",
    "issue_number",
]

rows = []

if INPUT.exists():
    with INPUT.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

kanban = []

for index, row in enumerate(rows, 1):
    execution_status = (
        row.get("execution_status")
        or row.get("status")
        or "DISCOVERED"
    ).strip()

    estimated_hours = (row.get("estimated_hours") or "").strip()

    try:
        estimated_minutes = str(round(float(estimated_hours) * 60))
    except (TypeError, ValueError):
        estimated_minutes = ""

    kanban.append({
        "id": index,
        "status": execution_status,
        "source": row.get("source", ""),
        "title": row.get("task_title", ""),
        "reward": row.get("reward", ""),
        "url": row.get("url", ""),
        "complexity": row.get("execution_risk", ""),
        "estimated_minutes": estimated_minutes,
        "submitted_at": "",
        "paid_at": "",
        "amount_received": "",
        "rank_position": row.get("rank_position", ""),
        "is_current_best_target": row.get("is_current_best_target", ""),
        "payment_probability": row.get("payment_probability", ""),
        "final_execution_score": row.get("final_execution_score", ""),
        "recommended_action": row.get("recommended_action", ""),
        "organization": row.get("organization", ""),
        "repository": row.get("repository", ""),
        "issue_number": row.get("issue_number", ""),
    })

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

with OUTPUT.open("w", encoding="utf-8-sig", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(kanban)

print()
print("=" * 70)
print("KANBAN ECONÔMICO GERADO")
print("=" * 70)
print("Registros:", len(kanban))
print("Output:", OUTPUT)

if kanban:
    print()
    print("Primeiro alvo:")
    print("Status:", kanban[0]["status"])
    print("Título:", kanban[0]["title"])
    print("Recompensa:", kanban[0]["reward"])
    print("Score:", kanban[0]["final_execution_score"])
