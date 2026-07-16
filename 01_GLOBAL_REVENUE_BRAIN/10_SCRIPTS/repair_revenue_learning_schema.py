from __future__ import annotations

import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "11_DATA" / "global_revenue_brain.db"


SOURCE_REPUTATION_COLUMNS = {
    "total_opportunities": "INTEGER NOT NULL DEFAULT 0",
    "total_started": "INTEGER NOT NULL DEFAULT 0",
    "total_submitted": "INTEGER NOT NULL DEFAULT 0",
    "total_accepted": "INTEGER NOT NULL DEFAULT 0",
    "payment_confirmed": "INTEGER NOT NULL DEFAULT 0",
    "payment_failed": "INTEGER NOT NULL DEFAULT 0",
    "avg_reward": "REAL NOT NULL DEFAULT 0",
    "avg_received": "REAL NOT NULL DEFAULT 0",
    "avg_hours": "REAL NOT NULL DEFAULT 0",
    "payment_success_rate": "REAL NOT NULL DEFAULT 0",
    "conservative_success_rate": "REAL NOT NULL DEFAULT 0",
    "payout_speed": "REAL NOT NULL DEFAULT 0",
    "automation_success": "REAL NOT NULL DEFAULT 0",
    "confidence_score": "REAL NOT NULL DEFAULT 0",
    "roi_score": "REAL NOT NULL DEFAULT 0",
    "last_seen": "TEXT",
    "updated_at": "TEXT",
}


REVENUE_LEARNING_COLUMNS = {
    "source_name": "TEXT",
    "payment_method": "TEXT NOT NULL DEFAULT 'unknown'",
    "category": "TEXT NOT NULL DEFAULT 'unknown'",
    "observations": "INTEGER NOT NULL DEFAULT 0",
    "successful_payments": "INTEGER NOT NULL DEFAULT 0",
    "failed_payments": "INTEGER NOT NULL DEFAULT 0",
    "success_rate": "REAL NOT NULL DEFAULT 0",
    "conservative_success_rate": "REAL NOT NULL DEFAULT 0",
    "avg_reward": "REAL NOT NULL DEFAULT 0",
    "avg_received": "REAL NOT NULL DEFAULT 0",
    "avg_hours": "REAL NOT NULL DEFAULT 0",
    "roi_score": "REAL NOT NULL DEFAULT 0",
    "confidence": "REAL NOT NULL DEFAULT 0",
    "updated_at": "TEXT",
}


REVENUE_FEEDBACK_COLUMNS = {
    "candidate_key": "TEXT",
    "opportunity_url": "TEXT",
    "source_name": "TEXT",
    "category": "TEXT",
    "execution_result": "TEXT",
    "reward_received": "REAL NOT NULL DEFAULT 0",
    "payment_currency": "TEXT",
    "payment_method": "TEXT",
    "execution_hours": "REAL NOT NULL DEFAULT 0",
    "roi": "REAL NOT NULL DEFAULT 0",
    "automation_level": "REAL NOT NULL DEFAULT 0",
    "paid": "INTEGER NOT NULL DEFAULT 0",
    "evidence_verified": "INTEGER NOT NULL DEFAULT 0",
    "confidence_before": "REAL NOT NULL DEFAULT 0",
    "confidence_after": "REAL NOT NULL DEFAULT 0",
    "learned": "INTEGER NOT NULL DEFAULT 0",
    "created_at": "TEXT",
    "updated_at": "TEXT",
}


def table_exists(
    connection: sqlite3.Connection,
    table: str,
) -> bool:
    return bool(
        connection.execute(
            """
            SELECT COUNT(*)
            FROM sqlite_master
            WHERE type = 'table'
              AND name = ?
            """,
            (table,),
        ).fetchone()[0]
    )


def columns(
    connection: sqlite3.Connection,
    table: str,
) -> set[str]:
    return {
        str(row[1])
        for row in connection.execute(
            f'PRAGMA table_info("{table}")'
        ).fetchall()
    }


def add_missing_columns(
    connection: sqlite3.Connection,
    table: str,
    required: dict[str, str],
) -> list[str]:
    existing = columns(
        connection,
        table,
    )

    added: list[str] = []

    for name, definition in required.items():
        if name in existing:
            continue

        connection.execute(
            f'''
            ALTER TABLE "{table}"
            ADD COLUMN "{name}" {definition}
            '''
        )

        added.append(name)

    return added


connection = sqlite3.connect(DB)

connection.executescript(
    """
    CREATE TABLE IF NOT EXISTS source_reputation (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_name TEXT UNIQUE
    );

    CREATE TABLE IF NOT EXISTS revenue_learning (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_name TEXT,
        payment_method TEXT DEFAULT 'unknown',
        category TEXT DEFAULT 'unknown'
    );

    CREATE TABLE IF NOT EXISTS revenue_feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        candidate_key TEXT
    );
    """
)

rep_added = add_missing_columns(
    connection,
    "source_reputation",
    SOURCE_REPUTATION_COLUMNS,
)

learning_added = add_missing_columns(
    connection,
    "revenue_learning",
    REVENUE_LEARNING_COLUMNS,
)

feedback_added = add_missing_columns(
    connection,
    "revenue_feedback",
    REVENUE_FEEDBACK_COLUMNS,
)

connection.execute(
    """
    UPDATE source_reputation
    SET updated_at = COALESCE(
        updated_at,
        CURRENT_TIMESTAMP
    )
    """
)

connection.execute(
    """
    UPDATE revenue_learning
    SET
        payment_method = COALESCE(
            NULLIF(payment_method, ''),
            'unknown'
        ),
        category = COALESCE(
            NULLIF(category, ''),
            'unknown'
        ),
        updated_at = COALESCE(
            updated_at,
            CURRENT_TIMESTAMP
        )
    """
)

connection.execute(
    """
    UPDATE revenue_feedback
    SET
        created_at = COALESCE(
            created_at,
            CURRENT_TIMESTAMP
        ),
        updated_at = COALESCE(
            updated_at,
            CURRENT_TIMESTAMP
        )
    """
)

# Remove duplicidades antes de criar índices únicos.
connection.execute(
    """
    DELETE FROM source_reputation
    WHERE id NOT IN (
        SELECT MIN(id)
        FROM source_reputation
        GROUP BY source_name
    )
      AND source_name IS NOT NULL
    """
)

connection.execute(
    """
    DELETE FROM revenue_learning
    WHERE id NOT IN (
        SELECT MIN(id)
        FROM revenue_learning
        GROUP BY
            source_name,
            payment_method,
            category
    )
    """
)

connection.execute(
    """
    DELETE FROM revenue_feedback
    WHERE id NOT IN (
        SELECT MIN(id)
        FROM revenue_feedback
        GROUP BY candidate_key
    )
      AND candidate_key IS NOT NULL
    """
)

connection.executescript(
    """
    CREATE UNIQUE INDEX IF NOT EXISTS
    ux_source_reputation_source_name
    ON source_reputation(source_name);

    CREATE UNIQUE INDEX IF NOT EXISTS
    ux_revenue_learning_identity
    ON revenue_learning(
        source_name,
        payment_method,
        category
    );

    CREATE UNIQUE INDEX IF NOT EXISTS
    ux_revenue_feedback_candidate_key
    ON revenue_feedback(candidate_key);

    CREATE INDEX IF NOT EXISTS
    idx_source_reputation_roi
    ON source_reputation(
        roi_score DESC,
        confidence_score DESC
    );

    CREATE INDEX IF NOT EXISTS
    idx_revenue_learning_roi
    ON revenue_learning(
        roi_score DESC,
        confidence DESC
    );

    CREATE INDEX IF NOT EXISTS
    idx_revenue_feedback_paid
    ON revenue_feedback(
        paid,
        evidence_verified,
        learned
    );
    """
)

connection.commit()

print()
print("===== REVENUE LEARNING SCHEMA REPAIR =====")
print("Database:", DB)
print(
    "source_reputation columns added:",
    rep_added or "none",
)
print(
    "revenue_learning columns added:",
    learning_added or "none",
)
print(
    "revenue_feedback columns added:",
    feedback_added or "none",
)

print()
print("===== REQUIRED COLUMN VALIDATION =====")

checks = {
    "source_reputation": SOURCE_REPUTATION_COLUMNS,
    "revenue_learning": REVENUE_LEARNING_COLUMNS,
    "revenue_feedback": REVENUE_FEEDBACK_COLUMNS,
}

failed = False

for table, required in checks.items():
    existing = columns(
        connection,
        table,
    )

    missing = sorted(
        set(required) - existing
    )

    print(
        f"{table}:",
        "OK" if not missing else f"MISSING {missing}",
    )

    if missing:
        failed = True

connection.close()

if failed:
    raise SystemExit(1)

print()
print("REVENUE LEARNING SCHEMA REPAIRED.")
