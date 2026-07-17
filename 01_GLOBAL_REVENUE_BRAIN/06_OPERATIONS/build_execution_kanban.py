import csv
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent

INPUT=ROOT/"04_OPPORTUNITIES"/"EXECUTION_READY_QUEUE.csv"
OUTPUT=ROOT/"06_OPERATIONS"/"EXECUTION_KANBAN.csv"

rows=[]

if INPUT.exists():
    with open(INPUT,encoding="utf-8-sig") as f:
        rows=list(csv.DictReader(f))

kanban=[]

for i,row in enumerate(rows,1):

    kanban.append({

        "id":i,

        "status":"DISCOVERED",

        "source":row.get("source",""),

        "title":row.get("task_title",""),

        "reward":row.get("reward",""),

        "url":row.get("url",""),

        "complexity":"",

        "estimated_minutes":"",

        "submitted_at":"",

        "paid_at":"",

        "amount_received":""

    })

with open(
    OUTPUT,
    "w",
    newline="",
    encoding="utf-8-sig"
) as f:

    w=csv.DictWriter(
        f,
        fieldnames=kanban[0].keys() if kanban else [
            "id",
            "status"
        ]
    )

    w.writeheader()

    if kanban:
        w.writerows(kanban)

print()
print("="*60)
print("Kanban:",len(kanban))
print(OUTPUT)
