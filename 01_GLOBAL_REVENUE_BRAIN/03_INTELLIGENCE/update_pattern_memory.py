import sqlite3

conn = sqlite3.connect("11_DATA/global_revenue_brain.db")

conn.execute("""
DELETE FROM revenue_pattern_memory
""")

conn.execute("""
INSERT INTO revenue_pattern_memory (

source,
category,
skill,
reward_bucket,
success_count,
failure_count,
total_revenue,
avg_roi,
avg_execution_hours

)

SELECT

source,

COALESCE(category,'unknown'),

COALESCE(skill,'unknown'),

CASE

WHEN reward < 100 THEN '0-99'
WHEN reward < 500 THEN '100-499'
WHEN reward < 1000 THEN '500-999'
WHEN reward < 5000 THEN '1000-4999'
ELSE '5000+'

END,

SUM(
CASE
WHEN execution_result='success'
THEN 1
ELSE 0
END
),

SUM(
CASE
WHEN execution_result<>'success'
THEN 1
ELSE 0
END
),

COALESCE(SUM(actual_revenue),0),

COALESCE(AVG(roi),0),

COALESCE(AVG(execution_time_hours),0)

FROM revenue_execution_history

GROUP BY

source,
category,
skill,

CASE

WHEN reward < 100 THEN '0-99'
WHEN reward < 500 THEN '100-499'
WHEN reward < 1000 THEN '500-999'
WHEN reward < 5000 THEN '1000-4999'
ELSE '5000+'

END
""")

conn.commit()

print()
print("===== PATTERN LEARNING UPDATE =====")

print(
"Patterns:",
conn.execute(
"SELECT COUNT(*) FROM revenue_pattern_memory"
).fetchone()[0]
)

print()

print("TOP PATTERNS")

for row in conn.execute("""

SELECT

source,
category,
skill,
reward_bucket,
success_count,
total_revenue,
avg_roi

FROM revenue_pattern_memory

ORDER BY

total_revenue DESC,
avg_roi DESC

LIMIT 20

"""):
    print(row)

conn.close()
