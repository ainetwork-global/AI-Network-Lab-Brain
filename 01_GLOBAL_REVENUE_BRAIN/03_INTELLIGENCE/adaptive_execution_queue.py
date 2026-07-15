import sqlite3

conn = sqlite3.connect("11_DATA/global_revenue_brain.db")

cols = {
    r[1]
    for r in conn.execute(
        "PRAGMA table_info(revenue_execution_queue)"
    )
}

if "adaptive_score" not in cols:
    conn.execute("""
    ALTER TABLE revenue_execution_queue
    ADD COLUMN adaptive_score REAL
    """)

conn.execute("""
UPDATE revenue_execution_queue
SET adaptive_score =
execution_priority
""")

conn.execute("""

UPDATE revenue_execution_queue

SET adaptive_score =

adaptive_score +

COALESCE(

(

SELECT

CASE

WHEN
(success_count+failure_count)=0

THEN 0

ELSE

(
CAST(success_count AS REAL)

/

(success_count+failure_count)

)

*20

END

FROM revenue_pattern_memory

WHERE
revenue_pattern_memory.source =
revenue_execution_queue.source

LIMIT 1

),

0

)

""")

conn.commit()

print()
print("===== ADAPTIVE EXECUTION QUEUE =====")

for row in conn.execute("""

SELECT

title,

reward,

execution_priority,

adaptive_score

FROM revenue_execution_queue

ORDER BY

adaptive_score DESC,
reward DESC

LIMIT 20

"""):

    print(row)

print()

print(
"TOTAL:",
conn.execute(
"SELECT COUNT(*) FROM revenue_execution_queue"
).fetchone()[0]
)

conn.close()
