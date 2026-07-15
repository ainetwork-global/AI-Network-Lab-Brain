from __future__ import annotations

import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "11_DATA" / "global_revenue_brain.db"


SCHEMA = """
CREATE TABLE IF NOT EXISTS opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_key TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_url TEXT NOT NULL,
    repository TEXT,
    author TEXT,
    description TEXT,
    published_at TEXT,
    discovered_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'discovered',
    currency TEXT,
    estimated_value REAL,
    capital_required REAL NOT NULL DEFAULT 0,
    financial_score REAL NOT NULL DEFAULT 0,
    confidence_score REAL NOT NULL DEFAULT 0,
    automation_score REAL NOT NULL DEFAULT 0,
    risk_score REAL NOT NULL DEFAULT 0,
    final_score REAL NOT NULL DEFAULT 0,
    score_reason TEXT,
    human_approval_required INTEGER NOT NULL DEFAULT 1,
    execution_notes TEXT,
    revenue_confirmed REAL NOT NULL DEFAULT 0,
    revenue_currency TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_opportunities_status
ON opportunities(status);

CREATE INDEX IF NOT EXISTS idx_opportunities_final_score
ON opportunities(final_score DESC);

CREATE INDEX IF NOT EXISTS idx_opportunities_category
ON opportunities(category);

CREATE TABLE IF NOT EXISTS scan_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL,
    sources_checked INTEGER NOT NULL DEFAULT 0,
    items_found INTEGER NOT NULL DEFAULT 0,
    items_inserted INTEGER NOT NULL DEFAULT 0,
    items_updated INTEGER NOT NULL DEFAULT 0,
    errors INTEGER NOT NULL DEFAULT 0,
    error_summary TEXT
);

CREATE TABLE IF NOT EXISTS source_health (
    source_key TEXT PRIMARY KEY,
    source_name TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_url TEXT,
    last_checked_at TEXT,
    last_success_at TEXT,
    last_error_at TEXT,
    consecutive_errors INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    last_items_found INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS revenue_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_key TEXT,
    event_type TEXT NOT NULL,
    amount REAL NOT NULL DEFAULT 0,
    currency TEXT,
    payment_destination TEXT,
    reference TEXT,
    confirmed INTEGER NOT NULL DEFAULT 0,
    occurred_at TEXT NOT NULL,
    notes TEXT
);
"""


def connect() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL;")
    connection.execute("PRAGMA synchronous=NORMAL;")
    connection.execute("PRAGMA busy_timeout=5000;")
    connection.executescript(SCHEMA)

    return connection


if __name__ == "__main__":
    with connect() as database:
        result = database.execute(
            "SELECT COUNT(*) AS total FROM opportunities"
        ).fetchone()

        print(f"Banco criado: {DATABASE_PATH}")
        print(f"Oportunidades existentes: {result['total']}")
