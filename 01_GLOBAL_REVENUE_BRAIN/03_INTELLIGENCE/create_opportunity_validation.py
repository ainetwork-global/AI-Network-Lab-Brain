import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "11_DATA" / "global_revenue_brain.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS opportunity_validation (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    source TEXT,
    title TEXT,
    url TEXT,

    payment_confirmed INTEGER DEFAULT 0,
    payment_method TEXT,

    automation_possible INTEGER DEFAULT 0,

    powershell_possible INTEGER DEFAULT 0,

    ai_possible INTEGER DEFAULT 0,

    wallet_supported INTEGER DEFAULT 0,

    stripe_supported INTEGER DEFAULT 0,

    nomad_supported INTEGER DEFAULT 0,

    execution_priority REAL DEFAULT 0,

    validation_notes TEXT,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP

)
""")

conn.commit()

print()
print("===== OPPORTUNITY VALIDATION =====")
print("Database:", DB)
print("Table: opportunity_validation READY")

conn.close()
