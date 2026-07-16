import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "11_DATA" / "global_revenue_brain.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("""
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
)
""")

conn.commit()

print()
print("===== REVENUE LEARNING TABLE =====")
print("Database:", DB)
print("Table ready: revenue_learning")

conn.close()
