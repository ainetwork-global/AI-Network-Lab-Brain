import sqlite3

conn = sqlite3.connect("11_DATA/global_revenue_brain.db")

print()
print("===== SOURCE DIVERSITY =====")

github_sources = conn.execute("""
SELECT COUNT(DISTINCT source)
FROM opportunity_verifications
""").fetchone()[0]

official_sources = conn.execute("""
SELECT COUNT(DISTINCT source_name)
FROM official_source_candidates
""").fetchone()[0]

algora_orgs = conn.execute("""
SELECT COUNT(DISTINCT organization)
FROM algora_open_bounties
""").fetchone()[0]

print(f"GitHub: {github_sources}")
print(f"Official: {official_sources}")
print(f"Algora: {algora_orgs}")

print()
print("===== OFFICIAL SOURCES =====")

for row in conn.execute("""

SELECT

source_name,
COUNT(*) total

FROM official_source_candidates

GROUP BY source_name

ORDER BY total DESC

"""):

    print(row)

conn.close()
