import sqlite3

conn = sqlite3.connect("11_DATA/global_revenue_brain.db")

cols = {
    r[1]
    for r in conn.execute(
        "PRAGMA table_info(revenue_execution_queue)"
    )
}

if "pattern_bonus" not in cols:
    conn.execute("""
    ALTER TABLE revenue_execution_queue
    ADD COLUMN pattern_bonus REAL DEFAULT 0
    """)

conn.execute("""
UPDATE revenue_execution_queue
SET pattern_bonus =
COALESCE(
(
SELECT
pattern_weight * 20
FROM revenue_pattern_memory
WHERE revenue_pattern_memory.source =
      revenue_execution_queue.source
LIMIT 1
),
0
)
""")

conn.execute("""
UPDATE revenue_execution_queue
SET adaptive_score =
execution_priority +
COALESCE(pattern_bonus,0)
""")

conn.commit()

print()
print("===== EXECUTION QUEUE WITH PATTERN BONUS =====")

for row in conn.execute("""

SELECT

title,
reward,
execution_priority,
pattern_bonus,
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
