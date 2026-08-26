from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "10_SCRIPTS"))
sys.path.insert(0, str(ROOT / "02_DISCOVERY"))

from database import connect
from global_revenue_hunter import build_key, save_opportunity


def main() -> int:
    inserted = 0
    updated = 0
    skipped = 0

    with connect() as database:
        table = database.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='algora_open_bounties'"
        ).fetchone()
        if not table:
            print("Algora table not found; nothing to import.")
            return 0

        rows = database.execute(
            """
            SELECT *
            FROM algora_open_bounties
            WHERE open_status = 1
              AND reward_amount > 0
              AND verification_status = 'staged'
            ORDER BY candidate_score DESC, reward_amount DESC
            """
        ).fetchall()

        for row in rows:
            url = row["github_url"] or row["algora_url"]
            if not url:
                skipped += 1
                continue

            description = (
                f"Explicit Algora open bounty. "
                f"Reward: {row['reward_currency']} {row['reward_amount']}. "
                f"Skills: {row['skills'] or 'not identified'}. "
                f"Claims: {row['claim_count'] if row['claim_count'] is not None else 'unknown'}. "
                f"Algora: {row['algora_url']}"
            )
            repository = "/".join(
                part for part in (
                    row["github_owner"],
                    row["github_repository"],
                ) if part
            )
            result = save_opportunity(
                database,
                {
                    "opportunity_key": build_key("algora", row["candidate_key"]),
                    "title": row["title"],
                    "category": "coding_bounty",
                    "source_name": "Algora Open Bounties",
                    "source_type": "algora_official",
                    "source_url": url,
                    "repository": repository,
                    "author": row["organization"],
                    "description": description,
                    "published_at": row["last_seen_at"],
                },
            )
            if result == "inserted":
                inserted += 1
            else:
                updated += 1

        database.commit()

    print(f"Algora imported: inserted={inserted}, updated={updated}, skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
