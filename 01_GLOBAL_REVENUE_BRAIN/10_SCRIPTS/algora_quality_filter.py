import sqlite3

conn = sqlite3.connect("11_DATA/global_revenue_brain.db")

conn.execute("""
DELETE FROM algora_open_bounties
WHERE
    algora_url LIKE 'tel:%'
    OR algora_url LIKE '%cal.com%'
    OR algora_url LIKE '%x.com/%'
    OR algora_url LIKE '%twitter.com/%'
    OR algora_url LIKE '%linkedin.com%'
    OR algora_url LIKE '%youtube.com%'
    OR algora_url LIKE '%medium.com%'
    OR algora_url LIKE '%blog%'
    OR (
        github_url IS NULL
        AND algora_url NOT LIKE 'https://algora.io/%/bounties/%'
    );
""")

conn.commit()

print()
print("===== ALGORA QUALITY FILTER =====")

for row in conn.execute("""
SELECT
organization,
COUNT(*)
FROM algora_open_bounties
GROUP BY organization
ORDER BY COUNT(*) DESC;
"""):
    print(row)

print()

print("TOTAL:")
print(
    conn.execute(
        "SELECT COUNT(*) FROM algora_open_bounties"
    ).fetchone()[0]
)

conn.close()
