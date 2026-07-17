import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

OUTPUT = ROOT/"04_OPPORTUNITIES"/"GLOBAL_DISCOVERY_QUEUE.csv"

INPUTS = [

ROOT/"04_OPPORTUNITIES"/"github_search_api_candidates.csv",

ROOT/"04_OPPORTUNITIES"/"GLOBAL_EXECUTION_QUEUE.csv",

ROOT/"04_OPPORTUNITIES"/"verified_opportunities.csv"

]

FIELDS = [

"source",
"repository",
"issue_number",
"title",
"url"

]

seen=set()

rows=[]

for file in INPUTS:

    if not file.exists():
        continue

    with file.open(
        encoding="utf-8-sig",
        newline=""
    ) as f:

        reader=csv.DictReader(f)

        for r in reader:

            repository=(
                r.get("repository")
                or r.get("organization")
                or ""
            )

            issue=(
                r.get("issue_number")
                or r.get("number")
                or ""
            )

            url=(
                r.get("url")
                or r.get("source_url")
                or ""
            )

            title=r.get("title","")

            key=(repository,issue)

            if key in seen:
                continue

            seen.add(key)

            rows.append({

                "source":file.name,

                "repository":repository,

                "issue_number":issue,

                "title":title,

                "url":url

            })

OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True
)

with OUTPUT.open(
    "w",
    newline="",
    encoding="utf-8-sig"
) as f:

    writer=csv.DictWriter(
        f,
        fieldnames=FIELDS
    )

    writer.writeheader()

    writer.writerows(rows)

print()

print("="*70)

print("GLOBAL DISCOVERY QUEUE")

print("="*70)

print("Sources:",len(INPUTS))

print("Unique Opportunities:",len(rows))

print("Output:",OUTPUT)
