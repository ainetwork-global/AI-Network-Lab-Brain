import csv
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

INPUT=ROOT/"04_OPPORTUNITIES"/"GLOBAL_DISCOVERY_QUEUE.csv"
OUTPUT=ROOT/"04_OPPORTUNITIES"/"DISCOVERY_INTELLIGENCE_QUEUE.csv"

BONUS=[

("payment",30),
("reward",30),
("bounty",35),
("paid",25),
("crypto",20),
("bitcoin",25),
("ethereum",20),
("usdc",20),
("bug",15),
("security",15),
("wallet",20),
("agent",15),
("ai",10),
("grant",20),
("competition",15)

]

rows=[]

with INPUT.open(
    encoding="utf-8-sig",
    newline=""
) as f:

    reader=csv.DictReader(f)

    fields=list(reader.fieldnames)

    fields.extend([
        "discovery_score",
        "discovery_priority"
    ])

    for row in reader:

        text=(
            row.get("title","")+" "+
            row.get("repository","")
        ).lower()

        score=0

        for word,value in BONUS:

            if re.search(r"\b"+re.escape(word)+r"\b",text):
                score+=value

        if score>=90:
            priority="VERY_HIGH"
        elif score>=60:
            priority="HIGH"
        elif score>=30:
            priority="MEDIUM"
        else:
            priority="LOW"

        row["discovery_score"]=score
        row["discovery_priority"]=priority

        rows.append(row)

rows.sort(
    key=lambda r:int(r["discovery_score"]),
    reverse=True
)

with OUTPUT.open(
    "w",
    newline="",
    encoding="utf-8-sig"
) as f:

    writer=csv.DictWriter(f,fieldnames=fields)

    writer.writeheader()

    writer.writerows(rows)

print("="*70)
print("DISCOVERY INTELLIGENCE")
print("="*70)
print("Candidates:",len(rows))
print("Output:",OUTPUT)
