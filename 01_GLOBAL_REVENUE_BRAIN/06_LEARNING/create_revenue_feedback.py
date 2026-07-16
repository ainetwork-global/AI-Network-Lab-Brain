import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "11_DATA" / "global_revenue_brain.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS revenue_feedback (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    opportunity_url TEXT,

    source_name TEXT,

    category TEXT,

    execution_result TEXT,

    reward_received REAL DEFAULT 0,

    payment_currency TEXT,

    payment_method TEXT,

    execution_hours REAL,

    roi REAL,

    automation_level REAL,

    paid INTEGER DEFAULT 0,

    confidence_before REAL,

    confidence_after REAL,

    learned BOOLEAN DEFAULT 0,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP

)
""")

conn.commit()

print()
print("===== REVENUE FEEDBACK ENGINE =====")
print("Database:", DB)
print("Table: revenue_feedback READY")

conn.close()
