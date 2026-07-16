import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "11_DATA" / "global_revenue_brain.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS source_reputation (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    source_name TEXT UNIQUE,

    total_opportunities INTEGER DEFAULT 0,

    payment_confirmed INTEGER DEFAULT 0,

    payment_failed INTEGER DEFAULT 0,

    avg_reward REAL DEFAULT 0,

    avg_hours REAL DEFAULT 0,

    automation_success REAL DEFAULT 0,

    payout_speed REAL DEFAULT 0,

    confidence_score REAL DEFAULT 0,

    last_seen DATETIME,

    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP

)
""")

conn.commit()

print()
print("===== SOURCE REPUTATION =====")
print("Database:", DB)
print("Table: source_reputation READY")

conn.close()
