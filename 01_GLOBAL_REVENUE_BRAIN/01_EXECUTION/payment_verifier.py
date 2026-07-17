import csv
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent

QUEUE=ROOT/"04_OPPORTUNITIES"/"GLOBAL_EXECUTION_QUEUE.csv"
OUT=ROOT/"04_OPPORTUNITIES"/"PAYMENT_VERIFIED_QUEUE.csv"

rows=[]

if QUEUE.exists():

    with open(
        QUEUE,
        encoding="utf-8-sig"
    ) as f:

        rows=list(csv.DictReader(f))

for r in rows:

    score=0

    reward=(r.get("reward") or "").strip()

    payment=(r.get("payment_type") or "").lower()

    url=(r.get("url") or "").lower()

    source=(r.get("source") or "").lower()

    if reward:
        score+=35

    if payment not in ("","unknown"):
        score+=20

    if any(x in url for x in (
        "github",
        "algora",
        "gitcoin",
        "immunefi",
        "bugcrowd",
        "hackerone",
        "devpost"
    )):
        score+=20

    if source in (
        "github",
        "algora",
        "gitcoin",
        "immunefi",
        "bugcrowd",
        "hackerone",
        "devpost"
    ):
        score+=15

    if "bounty" in (
        r.get("task_title","").lower()
    ):
        score+=10

    r["payment_verification_score"]=score

rows.sort(
    key=lambda x:int(x["payment_verification_score"]),
    reverse=True
)

with open(
    OUT,
    "w",
    newline="",
    encoding="utf-8-sig"
) as f:

    w=csv.DictWriter(
        f,
        fieldnames=list(rows[0].keys()) if rows else [
            "payment_verification_score"
        ]
    )

    w.writeheader()

    if rows:
        w.writerows(rows)

print()
print("Verified:",len(rows))
print("Output:",OUT)
