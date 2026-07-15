import sqlite3

conn = sqlite3.connect("11_DATA/global_revenue_brain.db")
conn.row_factory = sqlite3.Row

print()
print("===== SOURCE DIVERSITY =====")

queries = [

("GitHub",
"""
SELECT COUNT(DISTINCT source)
FROM opportunity_verifications
"""
),

("Official",
"""
SELECT COUNT(DISTINCT source)
FROM official_source_candidates
"""
),

("Algora",
"""
SELECT COUNT(DISTINCT organization)
FROM algora_open_bounties
"""
)

]

for name,sql in queries:
    total = conn.execute(sql).fetchone()[0]
    print(f"{name}: {total}")

print()
print("===== OFFICIAL SOURCES =====")

for row in conn.execute("""

SELECT
source,
COUNT(*) total

FROM official_source_candidates

GROUP BY source

ORDER BY total DESC

"""):
    print(row)

conn.close()
