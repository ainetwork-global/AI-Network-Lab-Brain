"""
GitHub Search API Discovery
Global Revenue Brain

Objetivo:
Descobrir novas oportunidades utilizando a Search API oficial
do GitHub e alimentar o Brain.
"""

import csv
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]

OUTPUT = ROOT / "04_OPPORTUNITIES" / "github_search_api_candidates.csv"

TOKEN = (
    os.getenv("GITHUB_TOKEN")
    or os.getenv("GH_TOKEN")
    or ""
).strip()

HEADERS = {
    "Accept":"application/vnd.github+json",
    "User-Agent":"GlobalRevenueBrain"
}

if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"

SEARCHES = [

    'is:issue is:open bounty',

    'is:issue is:open reward',

    'is:issue is:open bug bounty',

    'is:issue is:open payment',

    'is:issue is:open paid',

    'is:issue is:open "good first issue" reward',

    'is:issue is:open crypto reward',

]

FIELDS = [
    "query",
    "repository",
    "issue_number",
    "title",
    "url",
    "created_at",
    "updated_at"
]

rows=[]

for query in SEARCHES:

    url = (
        "https://api.github.com/search/issues?q=" +
        urllib.parse.quote(query) +
        "&per_page=100"
    )

    req = urllib.request.Request(url,headers=HEADERS)

    try:

        with urllib.request.urlopen(req,timeout=60) as r:

            data=json.loads(r.read())

    except Exception as e:

        print(query,e)

        continue

    for item in data.get("items",[]):

        repo=item["repository_url"].split("/")[-2:]

        rows.append({

            "query":query,

            "repository":"/".join(repo),

            "issue_number":item["number"],

            "title":item["title"],

            "url":item["html_url"],

            "created_at":item["created_at"],

            "updated_at":item["updated_at"]

        })

OUTPUT.parent.mkdir(parents=True,exist_ok=True)

with OUTPUT.open(
    "w",
    newline="",
    encoding="utf-8-sig"
) as f:

    writer=csv.DictWriter(f,fieldnames=FIELDS)

    writer.writeheader()

    writer.writerows(rows)

print()

print("="*70)

print("GITHUB SEARCH API DISCOVERY")

print("="*70)

print("Generated:",datetime.now(timezone.utc))

print("Candidates:",len(rows))

print("Output:",OUTPUT)
