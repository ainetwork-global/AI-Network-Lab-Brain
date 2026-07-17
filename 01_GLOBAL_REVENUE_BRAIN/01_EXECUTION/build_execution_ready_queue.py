import csv
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent

INPUT=ROOT/"04_OPPORTUNITIES"/"PAYMENT_VERIFIED_QUEUE.csv"
OUTPUT=ROOT/"04_OPPORTUNITIES"/"EXECUTION_READY_QUEUE.csv"

rows=[]

if INPUT.exists():
    with open(INPUT,encoding="utf-8-sig") as f:
        rows=list(csv.DictReader(f))

def classify(r):

    title=(r.get("task_title","")+" "+r.get("description","")).lower()

    deliverables=[]

    if any(x in title for x in ["python","script","automation"]):
        deliverables.append("python_code")

    if any(x in title for x in ["readme","documentation","docs"]):
        deliverables.append("documentation")

    if any(x in title for x in ["bug","fix","issue"]):
        deliverables.append("bug_fix")

    if any(x in title for x in ["test","testing"]):
        deliverables.append("tests")

    if not deliverables:
        deliverables.append("manual_review")

    r["deliverables"]=";".join(deliverables)
    r["execution_status"]="READY_FOR_PREPARATION"

    return r

rows=[classify(r) for r in rows]

with open(OUTPUT,"w",newline="",encoding="utf-8-sig") as f:

    w=csv.DictWriter(f,fieldnames=rows[0].keys() if rows else ["execution_status"])

    w.writeheader()

    if rows:
        w.writerows(rows)

print()
print("="*60)
print("Execution-ready:",len(rows))
print(OUTPUT)
