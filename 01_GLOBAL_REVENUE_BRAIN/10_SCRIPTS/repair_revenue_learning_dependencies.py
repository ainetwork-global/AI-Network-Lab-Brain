from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_DB = ROOT / "11_DATA" / "global_revenue_brain.db"
ACCIDENTAL_DB = Path.home() / "brain.db"
BACKUP_DIR = ROOT / "11_DATA" / "BACKUPS"


def table_exists(conn: sqlite3.Connection, table: str, schema: str = "main") -> bool:
    return bool(
        conn.execute(
            f"""
            SELECT COUNT(*)
            FROM {schema}.sqlite_master
            WHERE type = 'table'
              AND name = ?
            """,
            (table,),
        ).fetchone()[0]
    )


def columns(
    conn: sqlite3.Connection,
    table: str,
    schema: str = "main",
) -> list[str]:
    return [
        row[1]
        for row in conn.execute(
            f"PRAGMA {schema}.table_info({table})"
        ).fetchall()
    ]


BACKUP_DIR.mkdir(parents=True, exist_ok=True)

print()
print("===== REVENUE DATABASE REPAIR =====")
print("Official DB:", OFFICIAL_DB)
print("Accidental DB:", ACCIDENTAL_DB)
print("Accidental exists:", ACCIDENTAL_DB.exists())

if ACCIDENTAL_DB.exists():
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = BACKUP_DIR / f"accidental-brain-{timestamp}.db"
    shutil.copy2(ACCIDENTAL_DB, backup_path)
    print("Backup created:", backup_path)

conn = sqlite3.connect(OFFICIAL_DB)

conn.executescript(
    """
    CREATE TABLE IF NOT EXISTS settlement_methods (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        opportunity_id INTEGER,
        payment_method TEXT,
        currency TEXT,
        settlement_target TEXT,
        automation_level TEXT,
        verification_required INTEGER DEFAULT 0,
        estimated_delay_hours REAL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS revenue_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        opportunity_id INTEGER,
        source_name TEXT,
        payment_method TEXT,
        currency TEXT,
        expected_reward REAL,
        received_reward REAL,
        execution_hours REAL,
        status TEXT,
        completed_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS revenue_learning (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_name TEXT,
        payment_method TEXT,
        success_rate REAL,
        avg_reward REAL,
        avg_hours REAL,
        roi_score REAL,
        confidence REAL,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_settlement_opportunity
    ON settlement_methods(opportunity_id);

    CREATE INDEX IF NOT EXISTS idx_revenue_results_source
    ON revenue_results(source_name, payment_method);

    CREATE INDEX IF NOT EXISTS idx_revenue_learning_roi
    ON revenue_learning(roi_score DESC);
    """
)

copied = {}

if ACCIDENTAL_DB.exists():
    conn.execute(
        "ATTACH DATABASE ? AS accidental",
        (str(ACCIDENTAL_DB),),
    )

    for table in ("settlement_methods", "revenue_results"):
        if not table_exists(conn, table, "accidental"):
            copied[table] = 0
            continue

        official_columns = columns(conn, table, "main")
        accidental_columns = columns(conn, table, "accidental")

        transferable = [
            column
            for column in official_columns
            if column != "id"
            and column in accidental_columns
        ]

        if not transferable:
            copied[table] = 0
            continue

        column_sql = ", ".join(
            f'"{column}"'
            for column in transferable
        )

        before = conn.execute(
            f"SELECT COUNT(*) FROM main.{table}"
        ).fetchone()[0]

        if table == "settlement_methods":
            conn.execute(
                f"""
                INSERT INTO main.{table} ({column_sql})
                SELECT {column_sql}
                FROM accidental.{table} source
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM main.{table} target
                    WHERE COALESCE(target.opportunity_id, -1)
                          = COALESCE(source.opportunity_id, -1)
                      AND COALESCE(target.payment_method, '')
                          = COALESCE(source.payment_method, '')
                      AND COALESCE(target.currency, '')
                          = COALESCE(source.currency, '')
                      AND COALESCE(target.settlement_target, '')
                          = COALESCE(source.settlement_target, '')
                )
                """
            )
        else:
            conn.execute(
                f"""
                INSERT INTO main.{table} ({column_sql})
                SELECT {column_sql}
                FROM accidental.{table} source
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM main.{table} target
                    WHERE COALESCE(target.opportunity_id, -1)
                          = COALESCE(source.opportunity_id, -1)
                      AND COALESCE(target.source_name, '')
                          = COALESCE(source.source_name, '')
                      AND COALESCE(target.payment_method, '')
                          = COALESCE(source.payment_method, '')
                      AND COALESCE(target.completed_at, '')
                          = COALESCE(source.completed_at, '')
                )
                """
            )

        after = conn.execute(
            f"SELECT COUNT(*) FROM main.{table}"
        ).fetchone()[0]

        copied[table] = after - before

    conn.commit()
    conn.execute("DETACH DATABASE accidental")
else:
    conn.commit()

print()
print("===== OFFICIAL DATABASE STATUS =====")

for table in (
    "settlement_methods",
    "revenue_results",
    "revenue_learning",
):
    total = conn.execute(
        f"SELECT COUNT(*) FROM {table}"
    ).fetchone()[0]

    print(f"{table}: EXISTS — rows={total}")

print()
print("===== MIGRATION RESULT =====")
print(
    "settlement_methods copied:",
    copied.get("settlement_methods", 0),
)
print(
    "revenue_results copied:",
    copied.get("revenue_results", 0),
)

conn.close()
