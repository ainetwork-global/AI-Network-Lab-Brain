from __future__ import annotations

import csv
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import feedparser


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_FILE = PROJECT_ROOT / "04_OPPORTUNITIES" / "opportunities.csv"

FEEDS = [
    {
        "name": "Gitcoin",
        "category": "grants",
        "url": "https://gitcoin.co/blog/feed/",
    },
    {
        "name": "HackerOne",
        "category": "bug_bounty",
        "url": "https://www.hackerone.com/blog.rss",
    },
    {
        "name": "Devpost",
        "category": "hackathons",
        "url": "https://devpost.com/blog/feed",
    },
]


def build_id(source: str, link: str, title: str) -> str:
    raw = f"{source}|{link}|{title}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:20]


def ensure_output_file() -> None:
    if OUTPUT_FILE.exists():
        return

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "opportunity_id",
                "title",
                "category",
                "source_name",
                "source_url",
                "status",
                "capital_required",
                "discovered_at",
                "published_at",
                "summary",
            ]
        )


def existing_ids() -> set[str]:
    ensure_output_file()

    with OUTPUT_FILE.open("r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        return {
            row["opportunity_id"]
            for row in reader
            if row.get("opportunity_id")
        }


def scan() -> int:
    known_ids = existing_ids()
    new_rows: list[list[str]] = []
    discovered_at = datetime.now(timezone.utc).isoformat()

    for source in FEEDS:
        feed = feedparser.parse(source["url"])

        for entry in feed.entries[:30]:
            title = str(entry.get("title", "")).strip()
            link = str(entry.get("link", "")).strip()
            summary = str(entry.get("summary", "")).strip()
            published = str(entry.get("published", "")).strip()

            if not title or not link:
                continue

            opportunity_id = build_id(source["name"], link, title)

            if opportunity_id in known_ids:
                continue

            new_rows.append(
                [
                    opportunity_id,
                    title,
                    source["category"],
                    source["name"],
                    link,
                    "discovered",
                    "0",
                    discovered_at,
                    published,
                    summary.replace("\n", " ").replace("\r", " "),
                ]
            )

            known_ids.add(opportunity_id)

    if new_rows:
        with OUTPUT_FILE.open("a", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file)
            writer.writerows(new_rows)

    print(f"Novas oportunidades encontradas: {len(new_rows)}")
    print(f"Arquivo: {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(scan())
