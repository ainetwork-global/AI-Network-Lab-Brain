import sqlite3

conn = sqlite3.connect("11_DATA/global_revenue_brain.db")

columns = {
    row[1]
    for row in conn.execute(
        "PRAGMA table_info(algora_open_bounties)"
    )
}

required = {
    "completion_status":"TEXT",
    "completion_confidence":"REAL",
    "winner_detected":"INTEGER",
    "payment_confirmed":"INTEGER",
    "last_verification":"TEXT"
}

for name,ctype in required.items():
    if name not in columns:
        conn.execute(
            f"ALTER TABLE algora_open_bounties "
            f"ADD COLUMN {name} {ctype}"
        )

conn.commit()

print()
print("===== ALGORA COMPLETION LAYER =====")

for row in conn.execute("""
SELECT
COUNT(*)
FROM algora_open_bounties
"""):
    print("Bounties:",row[0])

print()

print("Completion columns installed.")

conn.close()
