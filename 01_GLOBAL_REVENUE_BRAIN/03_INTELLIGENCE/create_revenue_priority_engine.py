import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "11_DATA" / "global_revenue_brain.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS revenue_priority (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    opportunity_url TEXT UNIQUE,

    source_name TEXT,

    expected_reward REAL,

    expected_hours REAL,

    reward_per_hour REAL,

    payment_probability REAL,

    automation_score REAL,

    source_confidence REAL,

    execution_cost REAL,

    settlement_score REAL,

    competition_score REAL,

    freshness_score REAL,

    final_priority REAL,

    status TEXT DEFAULT 'pending',

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP

)
""")

conn.commit()

print()
print("===== REVENUE PRIORITY ENGINE =====")
print("Database:", DB)
print("Table: revenue_priority READY")

conn.close()
