import sqlite3

conn = sqlite3.connect("11_DATA/global_revenue_brain.db")

cols = {
    r[1]
    for r in conn.execute(
        "PRAGMA table_info(revenue_pattern_memory)"
    )
}

if "pattern_weight" not in cols:
    conn.execute("""
    ALTER TABLE revenue_pattern_memory
    ADD COLUMN pattern_weight REAL
    """)

conn.execute("""
UPDATE revenue_pattern_memory
SET pattern_weight =

CASE

WHEN success_count + failure_count = 0
THEN 0

ELSE

(
CAST(success_count AS REAL)

/

(success_count + failure_count)

)

END
""")

conn.commit()

print()
print("===== PATTERN WEIGHTS =====")

for row in conn.execute("""

SELECT

source,
category,
skill,
reward_bucket,
success_count,
failure_count,
ROUND(pattern_weight,3)

FROM revenue_pattern_memory

ORDER BY

pattern_weight DESC,
success_count DESC

LIMIT 20

"""):

    print(row)

print()

print(
"TOTAL:",
conn.execute(
"SELECT COUNT(*) FROM revenue_pattern_memory"
).fetchone()[0]
)

conn.close()
