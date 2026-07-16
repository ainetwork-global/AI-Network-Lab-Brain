import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "11_DATA" / "global_revenue_brain.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS scheduler_registry (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    module_name TEXT UNIQUE,

    enabled INTEGER DEFAULT 1,

    interval_minutes INTEGER NOT NULL,

    last_started_at DATETIME,

    last_finished_at DATETIME,

    last_status TEXT,

    next_run_at DATETIME,

    total_runs INTEGER DEFAULT 0,

    total_success INTEGER DEFAULT 0,

    total_failures INTEGER DEFAULT 0,

    average_runtime_seconds REAL DEFAULT 0,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP

)
""")

modules = [
    ("global_paid_work_discovery", 60),
    ("paid_task_execution_queue", 30),
    ("opportunity_validation", 30),
    ("source_reputation", 360),
    ("revenue_priority_engine", 30),
    ("revenue_feedback_engine", 60),
]

for name, interval in modules:
    cur.execute("""
        INSERT OR IGNORE INTO scheduler_registry
        (module_name, interval_minutes)
        VALUES (?, ?)
    """, (name, interval))

conn.commit()

print()
print("===== SCHEDULER REGISTRY =====")
print("Modules registered:", len(modules))

for row in cur.execute("""
    SELECT module_name, interval_minutes
    FROM scheduler_registry
    ORDER BY module_name
"""):
    print(f"{row[0]} -> {row[1]} min")

conn.close()
