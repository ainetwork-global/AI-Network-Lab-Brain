import sqlite3

conn = sqlite3.connect("11_DATA/global_revenue_brain.db")
conn.row_factory = sqlite3.Row

print()
print("===== REVENUE EXECUTION DASHBOARD =====")

summary = conn.execute("""

SELECT

COUNT(*) total,

SUM(reward) total_reward,

SUM(expected_value) total_expected,

AVG(adaptive_score) avg_score,

AVG(revenue_per_hour) avg_rph

FROM revenue_execution_queue

""").fetchone()

print(f"Opportunities : {summary['total']}")
print(f"Reward Pool   : USD {summary['total_reward'] or 0:.2f}")
print(f"Expected Pool : USD {summary['total_expected'] or 0:.2f}")
print(f"Avg Score     : {summary['avg_score'] or 0:.2f}")
print(f"Avg USD/hour  : {summary['avg_rph'] or 0:.2f}")

print()
print("===== TASK STATUS =====")

for row in conn.execute("""

SELECT
status,
COUNT(*)

FROM revenue_execution_tasks

GROUP BY status

ORDER BY COUNT(*) DESC

"""):
    print(f"{row['status']}: {row['COUNT(*)']}")

print()
print("===== VALIDATION STATUS =====")

for row in conn.execute("""

SELECT
validation_status,
COUNT(*)

FROM revenue_execution_tasks

GROUP BY validation_status

ORDER BY COUNT(*) DESC

"""):
    print(f"{row['validation_status']}: {row['COUNT(*)']}")

print()
print("===== TOP 10 BY EXPECTED VALUE =====")

for row in conn.execute("""

SELECT

title,
reward,
expected_value,
revenue_per_hour,
adaptive_score

FROM revenue_execution_queue

ORDER BY

expected_value DESC,
adaptive_score DESC

LIMIT 10

"""):

    print()
    print(row["title"])
    print(f"Reward         : USD {row['reward']}")
    print(f"Expected Value : USD {row['expected_value']}")
    print(f"Revenue/hour   : USD {row['revenue_per_hour']}")
    print(f"Adaptive Score : {row['adaptive_score']}")

conn.close()
