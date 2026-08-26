import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
conn = sqlite3.connect(PROJECT_ROOT / "11_DATA" / "global_revenue_brain.db")

conn.execute("""
CREATE TABLE IF NOT EXISTS revenue_execution_tasks(

id INTEGER PRIMARY KEY AUTOINCREMENT,

queue_id INTEGER,

title TEXT,

execution_type TEXT,

status TEXT DEFAULT 'pending',

attempts INTEGER DEFAULT 0,

priority REAL,

created_at TEXT DEFAULT CURRENT_TIMESTAMP,

started_at TEXT,

finished_at TEXT,

result TEXT

)
""")

conn.execute("DELETE FROM revenue_execution_tasks")

conn.execute("""

INSERT INTO revenue_execution_tasks(

queue_id,
title,
execution_type,
priority

)

SELECT

id,
title,

CASE

WHEN source='algora'
THEN 'github_issue'

ELSE 'manual_review'

END,

adaptive_score

FROM revenue_execution_queue

ORDER BY adaptive_score DESC

LIMIT 100

""")

conn.commit()

print()
print("===== EXECUTION TASK QUEUE =====")

for row in conn.execute("""

SELECT

title,
execution_type,
priority,
status

FROM revenue_execution_tasks

ORDER BY priority DESC

LIMIT 20

"""):
    print(row)

print()

print(
"TOTAL TASKS:",
conn.execute(
"SELECT COUNT(*) FROM revenue_execution_tasks"
).fetchone()[0]
)

conn.close()

