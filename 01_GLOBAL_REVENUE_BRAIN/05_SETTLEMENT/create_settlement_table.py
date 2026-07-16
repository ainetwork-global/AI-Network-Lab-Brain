import sqlite3

DB = "../brain.db"

con = sqlite3.connect(DB)
cur = con.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS settlement_methods(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_id INTEGER,
    payment_method TEXT,
    currency TEXT,
    settlement_target TEXT,
    automation_level TEXT,
    verification_required INTEGER,
    estimated_delay_hours REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

con.commit()

print("SETTLEMENT TABLE READY")
