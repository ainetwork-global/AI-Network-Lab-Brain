import sqlite3

conn = sqlite3.connect("11_DATA/global_revenue_brain.db")
conn.row_factory = sqlite3.Row

print()
print("===== REVENUE PIPELINE STATUS =====")

queries = {
    "Algora": """
        SELECT COUNT(*)
        FROM algora_open_bounties
    """,
    "Official Sources": """
        SELECT COUNT(*)
        FROM official_source_candidates
    """,
    "Verified Opportunities": """
        SELECT COUNT(*)
        FROM opportunity_verifications
        WHERE verification_status='verified'
    """,
}

for name, query in queries.items():
    total = conn.execute(query).fetchone()[0]
    print(f"{name}: {total}")

print()
print("===== TOP ACTIONABLE OPPORTUNITIES =====")

rows = conn.execute("""
SELECT
title,
organization,
reward_amount,
candidate_score,
github_url,
algora_url
FROM algora_open_bounties
ORDER BY
candidate_score DESC,
reward_amount DESC
LIMIT 15
""").fetchall()

for i,row in enumerate(rows,1):
    print()
    print(f"{i}. {row['title']}")
    print(f"   org: {row['organization']}")
    print(f"   reward: USD {row['reward_amount']}")
    print(f"   score: {row['candidate_score']}")
    print(f"   github: {row['github_url']}")
    print(f"   algora: {row['algora_url']}")

conn.close()
