from pathlib import Path
import csv

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/"02_DISCOVERY"/"DISCOVERED_SOURCES_QUEUE.csv"

FIELDS=[
"source_name",
"homepage",
"first_seen",
"discovered_by",
"country",
"language",
"category",
"supports_api",
"supports_rss",
"public_pages",
"payment_types",
"currencies",
"status",
"confidence"
]

if not OUT.exists():

    with open(OUT,"w",newline="",encoding="utf-8-sig") as f:

        csv.DictWriter(
            f,
            fieldnames=FIELDS
        ).writeheader()

print("QUEUE READY")
print(OUT)
