import sqlite3

conn = sqlite3.connect("11_DATA/global_revenue_brain.db")

conn.execute("""
CREATE TABLE IF NOT EXISTS revenue_execution_queue (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    source TEXT,
    source_id INTEGER,

    title TEXT,

    reward REAL,

    score REAL,

    probability REAL,

    expected_value REAL,

    execution_priority REAL,

    execution_status TEXT DEFAULT 'pending',

    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

conn.execute("DELETE FROM revenue_execution_queue")

conn.execute("""
INSERT INTO revenue_execution_queue(

source,
source_id,
title,
reward,
score,
probability,
expected_value,
execution_priority

)

SELECT

'algora',

id,

title,

COALESCE(reward_amount,0),

COALESCE(candidate_score,0),

CASE completion_status

WHEN 'open' THEN 0.95
WHEN 'unknown' THEN 0.40
ELSE 0.05

END,

COALESCE(reward_amount,0) *

CASE completion_status

WHEN 'open' THEN 0.95
WHEN 'unknown' THEN 0.40
ELSE 0.05

END,

(
COALESCE(candidate_score,0)
+
(
COALESCE(reward_amount,0)/100
)
)

FROM algora_open_bounties
""")

conn.commit()

print()
print("===== REVENUE EXECUTION QUEUE =====")

for row in conn.execute("""

SELECT

title,

reward,

execution_priority,

expected_value

FROM revenue_execution_queue

ORDER BY execution_priority DESC

LIMIT 20

"""):

    print()
    print(row)

print()

print(
"TOTAL:",
conn.execute(
"SELECT COUNT(*) FROM revenue_execution_queue"
).fetchone()[0]
)

conn.close()
