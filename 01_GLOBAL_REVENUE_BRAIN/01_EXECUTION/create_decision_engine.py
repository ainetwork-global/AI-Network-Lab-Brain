import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "11_DATA" / "global_revenue_brain.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS decision_engine (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    opportunity_id INTEGER,

    opportunity_type TEXT,

    source_name TEXT,

    expected_reward REAL,

    payment_probability REAL,

    execution_hours REAL,

    automation_score REAL,

    source_confidence REAL,

    settlement_target TEXT,

    roi_score REAL,

    final_decision_score REAL,

    recommended_action TEXT,

    human_review_required INTEGER DEFAULT 1,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP

)
""")

conn.commit()

print()
print("===== DECISION ENGINE =====")
print("Database:", DB)
print("decision_engine READY")

conn.close()
