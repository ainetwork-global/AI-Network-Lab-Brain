from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "10_SCRIPTS"))
sys.path.insert(0, str(ROOT / "02_DISCOVERY"))

from database import connect
from global_revenue_hunter import build_key, save_opportunity


def table_exists(database: sqlite3.Connection, name: str) -> bool:
    return database.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone() is not None


def persist(
    database: sqlite3.Connection,
    *,
    source_key: str,
    external_key: str,
    title: str,
    category: str,
    source_name: str,
    source_type: str,
    source_url: str,
    author: str,
    description: str,
    published_at: str,
    currency: str | None,
    estimated_value: float | None,
    capital_required: float = 0,
) -> str:
    opportunity_key = build_key(source_key, external_key)
    result = save_opportunity(
        database,
        {
            "opportunity_key": opportunity_key,
            "title": title,
            "category": category,
            "source_name": source_name,
            "source_type": source_type,
            "source_url": source_url,
            "repository": "",
            "author": author,
            "description": description,
            "published_at": published_at,
        },
    )
    database.execute(
        """
        UPDATE opportunities
        SET currency = COALESCE(?, currency),
            estimated_value = COALESCE(?, estimated_value),
            capital_required = ?,
            human_approval_required = 1,
            updated_at = datetime('now')
        WHERE opportunity_key = ?
        """,
        (currency, estimated_value, capital_required, opportunity_key),
    )
    return result


def import_paid_work(database: sqlite3.Connection) -> tuple[int, int]:
    if not table_exists(database, "paid_work_opportunities"):
        return 0, 0
    inserted = updated = 0
    rows = database.execute(
        """
        SELECT * FROM paid_work_opportunities
        WHERE discovery_status = 'actionable_review'
          AND explicit_payment = 1
          AND remote_confirmed = 1
          AND human_approval_required = 1
        ORDER BY discovery_score DESC
        LIMIT 300
        """
    ).fetchall()
    names = {
        "arbeitnow": "Arbeitnow",
        "remotive": "Remotive",
        "remoteok": "Remote OK",
        "github_paid_issues": "GitHub Paid Issues",
    }
    for row in rows:
        value = row["maximum_amount"] or row["minimum_amount"]
        result = persist(
            database,
            source_key="global_paid_work",
            external_key=row["candidate_key"],
            title=row["title"],
            category="paid_development" if row["source"] != "github_paid_issues" else "open_source_bounty",
            source_name=names.get(row["source"], row["source"]),
            source_type="global_paid_work_official_feed",
            source_url=row["url"],
            author=row["organization"] or "",
            description=(
                f"{row['description'] or ''} Payment evidence: {row['payment_evidence'] or row['salary'] or 'review required'}. "
                f"Location: {row['location'] or 'not stated'}. Application type: {row['application_type'] or 'review required'}."
            ),
            published_at=row["published_at"] or row["last_seen_at"],
            currency=row["currency"],
            estimated_value=value,
        )
        inserted += result == "inserted"
        updated += result == "updated"
    return inserted, updated


def import_devpost(database: sqlite3.Connection) -> tuple[int, int]:
    if not table_exists(database, "devpost_hackathons"):
        return 0, 0
    inserted = updated = 0
    rows = database.execute(
        """
        SELECT * FROM devpost_hackathons
        WHERE verification_status = 'staged'
          AND reward_amount > 0
          AND online = 1
          AND lower(status) NOT IN ('closed', 'ended', 'completed')
        ORDER BY candidate_score DESC, reward_amount DESC
        LIMIT 200
        """
    ).fetchall()
    for row in rows:
        result = persist(
            database,
            source_key="devpost",
            external_key=row["candidate_key"],
            title=row["title"],
            category="hackathon",
            source_name="Devpost Hackathons",
            source_type="devpost_official",
            source_url=row["url"],
            author=row["organization"] or "",
            description=(
                f"{row['description'] or ''} Prize pool: USD {row['reward_amount']}. "
                f"Deadline: {row['end_date'] or 'review required'}. Participants: {row['participants'] or 'unknown'}."
            ),
            published_at=row["last_seen_at"],
            currency=row["reward_currency"] or "USD",
            estimated_value=row["reward_amount"],
        )
        inserted += result == "inserted"
        updated += result == "updated"
    return inserted, updated


def import_official_sources(database: sqlite3.Connection) -> tuple[int, int]:
    if not table_exists(database, "official_source_candidates"):
        return 0, 0
    inserted = updated = 0
    rows = database.execute(
        """
        SELECT * FROM official_source_candidates
        WHERE verification_status = 'staged'
          AND reward_amount > 0
          AND capital_required = 0
          AND lower(COALESCE(status, 'open')) NOT IN ('closed', 'ended', 'completed')
        ORDER BY candidate_score DESC, reward_amount DESC
        LIMIT 300
        """
    ).fetchall()
    for row in rows:
        result = persist(
            database,
            source_key="official_source",
            external_key=row["candidate_key"],
            title=row["title"],
            category=row["category"],
            source_name=row["source_name"],
            source_type="official_global_source",
            source_url=row["url"],
            author="",
            description=(
                f"{row['description'] or ''} Reward evidence: {row['reward_evidence'] or 'review required'}. "
                f"Eligibility: {row['eligibility'] or 'manual review required'}. "
                f"KYC: {'required' if row['kyc_required'] else 'not identified'}."
            ),
            published_at=row["open_date"] or row["last_seen_at"],
            currency=row["reward_currency"],
            estimated_value=row["reward_amount"],
            capital_required=0,
        )
        inserted += result == "inserted"
        updated += result == "updated"
    return inserted, updated


def main() -> int:
    totals = {}
    with connect() as database:
        totals["paid_work"] = import_paid_work(database)
        totals["devpost"] = import_devpost(database)
        totals["official_sources"] = import_official_sources(database)
        database.commit()
    for source, (inserted, updated) in totals.items():
        print(f"{source}: inserted={inserted}, updated={updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
