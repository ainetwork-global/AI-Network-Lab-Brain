from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "11_DATA" / "global_revenue_brain.db"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

required = ("revenue_results", "revenue_learning")

for table in required:
    exists = conn.execute(
        """
        SELECT COUNT(*)
        FROM sqlite_master
        WHERE type='table' AND name=?
        """,
        (table,),
    ).fetchone()[0]

    if not exists:
        raise RuntimeError(f"Tabela obrigatória ausente: {table}")

conn.execute("DELETE FROM revenue_learning")

conn.execute(
    """
    INSERT INTO revenue_learning (
        source_name,
        payment_method,
        success_rate,
        avg_reward,
        avg_hours,
        roi_score,
        confidence,
        updated_at
    )
    SELECT
        COALESCE(source_name, 'unknown'),
        COALESCE(payment_method, 'unknown'),
        AVG(
            CASE
                WHEN COALESCE(received_reward, 0) > 0
                THEN 1.0
                ELSE 0.0
            END
        ),
        AVG(COALESCE(received_reward, 0)),
        AVG(COALESCE(execution_hours, 0)),
        CASE
            WHEN AVG(COALESCE(execution_hours, 0)) > 0
            THEN
                AVG(COALESCE(received_reward, 0))
                / AVG(COALESCE(execution_hours, 0))
            ELSE 0
        END,
        COUNT(*),
        ?
    FROM revenue_results
    GROUP BY
        COALESCE(source_name, 'unknown'),
        COALESCE(payment_method, 'unknown')
    """,
    (utc_now(),),
)

conn.commit()

rows = conn.execute(
    """
    SELECT
        source_name,
        payment_method,
        success_rate,
        avg_reward,
        avg_hours,
        roi_score,
        confidence
    FROM revenue_learning
    ORDER BY roi_score DESC, confidence DESC
    """
).fetchall()

print()
print("===== REVENUE LEARNING UPDATE =====")
print("Groups learned:", len(rows))

if not rows:
    print("Status: awaiting_real_revenue_results")
else:
    for row in rows:
        print(dict(row))

conn.close()
