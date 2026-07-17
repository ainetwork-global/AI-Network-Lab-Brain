import csv
import json
import urllib.request
from pathlib import Path
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parent.parent

OUT=ROOT/"04_OPPORTUNITIES"/"GLOBAL_EXECUTION_QUEUE.csv"

SEARCHES=[
'label:"help wanted"',
'label:"good first issue"',
'label:bounty',
'label:reward',
'label:bug',
'label:enhancement'
]

HEADERS={
"Accept":"application/vnd.github+json",
"User-Agent":"GlobalRevenueBrain"
}

rows=[]

for query in SEARCHES:

    url="https://api.github.com/search/issues?q="+query.replace(" ","+")

    try:

        req=urllib.request.Request(url,headers=HEADERS)

        data=json.loads(
            urllib.request.urlopen(req,timeout=30).read()
        )

    except Exception:
        continue

    for item in data.get("items",[]):

        rows.append({

            "source":"GitHub",

            "platform":"GitHub",

            "task_title":item.get("title",""),

            "description":item.get("html_url",""),

            "url":item.get("html_url",""),

            "country":"global",

            "language":"unknown",

            "currency":"unknown",

            "payment_type":"unknown",

            "reward":"",

            "estimated_hours":"",

            "required_skills":"",

            "execution_probability":"",

            "payment_probability":"",

            "receipt_probability":"",

            "competition_score":"",

            "expected_roi":"",

            "repeatability":"",

            "requires_human_action":"true",

            "status":"discovered",

            "discovered_at":datetime.now(
                timezone.utc
            ).isoformat(),

            "last_checked":datetime.now(
                timezone.utc
            ).isoformat()

        })

existing=[]

if OUT.exists():

    with open(
        OUT,
        encoding="utf-8-sig"
    ) as f:

        existing=list(csv.DictReader(f))

urls={
r["url"]
for r in existing
}

for r in rows:

    if r["url"] not in urls:

        existing.append(r)

with open(
OUT,
"w",
newline="",
encoding="utf-8-sig"
) as f:

    w=csv.DictWriter(
        f,
        fieldnames=[
"source",
"platform",
"task_title",
"description",
"url",
"country",
"language",
"currency",
"payment_type",
"reward",
"estimated_hours",
"required_skills",
"execution_probability",
"payment_probability",
"receipt_probability",
"competition_score",
"expected_roi",
"repeatability",
"requires_human_action",
"status",
"discovered_at",
"last_checked"
        ]
    )

    w.writeheader()
    w.writerows(existing)

print("GitHub opportunities:",len(existing))
