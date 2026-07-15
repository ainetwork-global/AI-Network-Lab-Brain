import sqlite3

conn = sqlite3.connect("11_DATA/global_revenue_brain.db")
conn.row_factory = sqlite3.Row

print("\n===== EXECUTABLE DIAGNOSTIC =====\n")

rows = conn.execute("""
SELECT
    title,
    explicit_reward,
    executable,
    link_active,
    verification_score,
    verification_status,
    reward_amount,
    reward_currency
FROM opportunity_verifications
LIMIT 30
""").fetchall()

for r in rows:
    print("="*70)
    print(r["title"])
    print(f"explicit_reward : {r['explicit_reward']}")
    print(f"executable      : {r['executable']}")
    print(f"link_active     : {r['link_active']}")
    print(f"reward          : {r['reward_currency']} {r['reward_amount']}")
    print(f"score           : {r['verification_score']}")
    print(f"status          : {r['verification_status']}")

conn.close()
