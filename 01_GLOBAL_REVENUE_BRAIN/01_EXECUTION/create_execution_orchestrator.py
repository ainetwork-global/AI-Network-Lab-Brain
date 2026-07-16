import sqlite3
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "11_DATA" / "global_revenue_brain.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS execution_history(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    module_name TEXT,

    started_at DATETIME,

    finished_at DATETIME,

    execution_seconds REAL,

    status TEXT,

    rows_processed INTEGER,

    notes TEXT

)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS execution_queue(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    module_name TEXT,

    priority REAL,

    scheduled_at DATETIME,

    status TEXT DEFAULT 'pending',

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP

)
""")

modules = [

"global_paid_work_discovery",

"paid_task_execution_queue",

"opportunity_validation",

"source_reputation",

"revenue_priority_engine",

"revenue_feedback_engine"

]

for order,module in enumerate(modules):

    cur.execute("""

    INSERT INTO execution_queue(

        module_name,

        priority,

        scheduled_at

    )

    VALUES(?,?,?)

    """,

    (

        module,

        100-order,

        datetime.utcnow()

    ))

conn.commit()

print()
print("===== EXECUTION ORCHESTRATOR =====")
print("Modules queued:",len(modules))

for row in cur.execute("""

SELECT

module_name,

priority

FROM execution_queue

ORDER BY priority DESC

"""):

    print(row)

conn.close()
