import csv
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent

QUEUE=ROOT/"04_OPPORTUNITIES"/"EXECUTION_READY_QUEUE.csv"
DOSSIERS=ROOT/"05_EXECUTION_DOSSIERS"

DOSSIERS.mkdir(parents=True,exist_ok=True)

rows=[]

if QUEUE.exists():
    with open(QUEUE,encoding="utf-8-sig") as f:
        rows=list(csv.DictReader(f))

def estimate(title):

    t=title.lower()

    if any(x in t for x in [
        "documentation",
        "readme",
        "translation"
    ]):
        return "VERY_LOW","15"

    if any(x in t for x in [
        "bug",
        "issue",
        "fix"
    ]):
        return "LOW","30"

    if any(x in t for x in [
        "python",
        "automation",
        "script"
    ]):
        return "MEDIUM","60"

    return "MANUAL","?"

for i,row in enumerate(rows,1):

    complexity,time=estimate(
        row.get("task_title","")
    )

    reward=row.get("reward","Unknown")

    md=f"""
# EXECUTION DOSSIER

ID: {i}

Title:
{row.get("task_title","")}

Source:
{row.get("source","")}

URL:
{row.get("url","")}

Reward:
{reward}

Complexity:
{complexity}

Estimated Time:
{time} minutes

Deliverables:
{row.get("deliverables","")}

Execution Status:
READY_FOR_HUMAN_REVIEW

Next Step:

Review opportunity.
Prepare deliverables.
Submit manually.
Record payment.
"""

    filename=DOSSIERS/f"dossier_{i:05}.md"

    filename.write_text(md,encoding="utf-8")

print()
print("="*60)
print("Execution dossiers:",len(rows))
print(DOSSIERS)

