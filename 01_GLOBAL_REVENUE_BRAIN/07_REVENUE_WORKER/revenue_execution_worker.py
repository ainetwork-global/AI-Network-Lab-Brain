import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

KANBAN = ROOT/"06_OPERATIONS"/"EXECUTION_KANBAN.csv"
OUTPUT = ROOT/"07_REVENUE_WORKER"/"NEXT_EXECUTION.md"

rows=[]

if KANBAN.exists():
    with open(KANBAN,encoding="utf-8-sig") as f:
        rows=list(csv.DictReader(f))

candidate=None

priority=[
    "READY",
    "DISCOVERED",
    "ANALYZED"
]

for status in priority:
    for row in rows:
        if row.get("status")==status:
            candidate=row
            break
    if candidate:
        break

if candidate is None and rows:
    candidate=rows[0]

if candidate:

    report=f"""# NEXT EXECUTION

Status:
{candidate.get("status","")}

Source:
{candidate.get("source","")}

Title:
{candidate.get("title","")}

Reward:
{candidate.get("reward","")}

URL:
{candidate.get("url","")}

Checklist

[ ] Abrir documentação
[ ] Validar requisitos
[ ] Produzir entregáveis
[ ] Revisar
[ ] Submeter manualmente
[ ] Registrar resultado
"""

else:

    report="# Nenhuma oportunidade encontrada."

OUTPUT.write_text(report,encoding="utf-8")

print("Worker generated:")
print(OUTPUT)

