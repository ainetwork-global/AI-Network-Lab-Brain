import sqlite3

conn = sqlite3.connect("11_DATA/global_revenue_brain.db")

cols = {
    r[1]
    for r in conn.execute(
        "PRAGMA table_info(revenue_execution_tasks)"
    )
}

required = {
    "lease_worker":"TEXT",
    "lease_until":"TEXT",
    "picked_at":"TEXT"
}

for c,t in required.items():
    if c not in cols:
        conn.execute(
            f"ALTER TABLE revenue_execution_tasks ADD COLUMN {c} {t}"
        )

conn.commit()

print()
print("===== EXECUTION LEASE LAYER =====")

print(
"Tasks:",
conn.execute(
"SELECT COUNT(*) FROM revenue_execution_tasks"
).fetchone()[0]
)

print()

print("Lease columns installed.")

conn.close()
