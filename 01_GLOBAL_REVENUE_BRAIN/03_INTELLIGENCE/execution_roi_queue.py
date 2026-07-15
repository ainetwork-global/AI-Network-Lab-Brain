import sqlite3

conn = sqlite3.connect("11_DATA/global_revenue_brain.db")

cols = {
    r[1]
    for r in conn.execute(
        "PRAGMA table_info(revenue_execution_queue)"
    )
}

if "estimated_hours" not in cols:
    conn.execute(
        "ALTER TABLE revenue_execution_queue ADD COLUMN estimated_hours REAL"
    )

if "revenue_per_hour" not in cols:
    conn.execute(
        "ALTER TABLE revenue_execution_queue ADD COLUMN revenue_per_hour REAL"
    )

conn.execute("""
UPDATE revenue_execution_queue
SET
estimated_hours =
CASE

WHEN reward>=5000 THEN 120

WHEN reward>=1000 THEN 60

WHEN reward>=500 THEN 30

WHEN reward>=100 THEN 12

ELSE 4

END
""")

conn.execute("""
UPDATE revenue_execution_queue
SET
revenue_per_hour =
CASE

WHEN estimated_hours>0

THEN expected_value/estimated_hours

ELSE expected_value

END
""")

conn.commit()

print()
print("===== ROI EXECUTION QUEUE =====")

for row in conn.execute("""

SELECT

title,

reward,

expected_value,

estimated_hours,

ROUND(revenue_per_hour,2)

FROM revenue_execution_queue

ORDER BY revenue_per_hour DESC,
expected_value DESC

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
