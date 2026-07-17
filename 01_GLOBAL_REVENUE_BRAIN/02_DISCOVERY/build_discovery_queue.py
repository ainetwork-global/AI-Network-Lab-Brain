import csv
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parent.parent

targets=json.loads(
(ROOT/"00_CURRENT_STATE"/"DISCOVERY_TARGETS.json").read_text(encoding="utf-8")
)

queries=[]

with open(
ROOT/"04_OPPORTUNITIES"/"GLOBAL_SEARCH_QUERY_INDEX.csv",
encoding="utf-8-sig"
) as f:

    queries=list(csv.DictReader(f))

queue=[]

for source in targets:

    for q in queries:

        queue.append({

            "source":source["name"],
            "source_type":source["type"],

            "query":q["search_query"],

            "status":"pending",

            "priority":100,

            "created_at":datetime.now(
                timezone.utc
            ).isoformat()

        })

out=ROOT/"02_DISCOVERY"/"DISCOVERY_QUEUE.csv"

with open(
out,
"w",
newline="",
encoding="utf-8-sig"
) as f:

    w=csv.DictWriter(
        f,
        fieldnames=[
            "source",
            "source_type",
            "query",
            "status",
            "priority",
            "created_at"
        ]
    )

    w.writeheader()

    w.writerows(queue)

print()
print("Discovery Queue:",len(queue))
print(out)
