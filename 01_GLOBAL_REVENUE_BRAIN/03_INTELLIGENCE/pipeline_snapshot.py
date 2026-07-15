import sqlite3

conn = sqlite3.connect("11_DATA/global_revenue_brain.db")

conn.execute("""
CREATE TABLE IF NOT EXISTS revenue_pipeline_snapshots(

id INTEGER PRIMARY KEY AUTOINCREMENT,

created_at TEXT DEFAULT CURRENT_TIMESTAMP,

opportunities INTEGER,

approved_tasks INTEGER,

pending_tasks INTEGER,

leased_tasks INTEGER,

reward_pool REAL,

expected_pool REAL,

avg_adaptive_score REAL,

avg_revenue_per_hour REAL

)
""")

conn.execute("""

INSERT INTO revenue_pipeline_snapshots(

opportunities,
approved_tasks,
pending_tasks,
leased_tasks,
reward_pool,
expected_pool,
avg_adaptive_score,
avg_revenue_per_hour

)

SELECT

(SELECT COUNT(*) FROM revenue_execution_queue),

(SELECT COUNT(*) FROM revenue_execution_tasks
WHERE validation_status='approved'),

(SELECT COUNT(*) FROM revenue_execution_tasks
WHERE status='pending'),

(SELECT COUNT(*) FROM revenue_execution_tasks
WHERE status='leased'),

COALESCE(SUM(reward),0),

COALESCE(SUM(expected_value),0),

COALESCE(AVG(adaptive_score),0),

COALESCE(AVG(revenue_per_hour),0)

FROM revenue_execution_queue

""")

conn.commit()

print()
print("===== PIPELINE SNAPSHOT =====")

row = conn.execute("""

SELECT *

FROM revenue_pipeline_snapshots

ORDER BY id DESC

LIMIT 1

""").fetchone()

for value in row:
    print(value)

print()

print(
"Snapshots:",
conn.execute(
"SELECT COUNT(*) FROM revenue_pipeline_snapshots"
).fetchone()[0]
)

conn.close()
