import csv
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent

PAYMENT=ROOT/"04_OPPORTUNITIES"/"PAYMENT_VERIFIED_QUEUE.csv"

REPORT=ROOT/"12_REPORTS"/"TODAYS_EXECUTION_PLAN.md"

rows=[]

if PAYMENT.exists():

    with open(
        PAYMENT,
        encoding="utf-8-sig"
    ) as f:

        rows=list(csv.DictReader(f))

def score(row):

    total=0

    try:
        total+=float(row.get("payment_verification_score",0))
    except:
        pass

    try:
        total+=float(row.get("execution_probability",0))
    except:
        pass

    try:
        total+=float(row.get("payment_probability",0))
    except:
        pass

    return total

rows.sort(
    key=score,
    reverse=True
)

top=rows[:10]

REPORT.parent.mkdir(
    parents=True,
    exist_ok=True
)

with open(
    REPORT,
    "w",
    encoding="utf-8"
) as f:

    f.write("# TODAY EXECUTION PLAN\n\n")

    f.write(f"Total opportunities: {len(rows)}\n\n")

    for i,r in enumerate(top,1):

        f.write(f"## {i}\n")
        f.write(f"Source: {r.get('source','')}\n")
        f.write(f"Title: {r.get('task_title','')}\n")
        f.write(f"URL: {r.get('url','')}\n")
        f.write(f"Payment Score: {r.get('payment_verification_score','')}\n")
        f.write("\n")

print("Top opportunities:",len(top))
print(REPORT)
