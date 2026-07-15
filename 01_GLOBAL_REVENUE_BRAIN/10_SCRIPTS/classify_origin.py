import sqlite3

conn = sqlite3.connect("11_DATA/global_revenue_brain.db")

conn.execute("""
UPDATE opportunity_verifications
SET origin='internal'
WHERE
lower(title) LIKE '%bounty alert%'
OR lower(title) LIKE '%tool discovery%'
OR lower(title) LIKE '%ops dashboard%'
OR lower(title) LIKE '%approval:%'
OR lower(title) LIKE '%claim-to-payout%'
OR lower(title) LIKE '%canary%'
OR lower(title) LIKE '%meta-bounty%'
OR lower(title) LIKE '%subscription%'
OR lower(title) LIKE '%wayfinder%'
""")

conn.execute("""
UPDATE opportunity_verifications
SET origin='external'
WHERE origin IS NULL
""")

conn.commit()

print()

for row in conn.execute("""
SELECT origin,
COUNT(*)
FROM opportunity_verifications
GROUP BY origin
"""):
    print(row)

conn.close()
