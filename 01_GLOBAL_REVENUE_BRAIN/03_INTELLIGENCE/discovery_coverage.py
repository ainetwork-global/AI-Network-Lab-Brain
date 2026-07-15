import sqlite3

conn = sqlite3.connect("11_DATA/global_revenue_brain.db")
conn.row_factory = sqlite3.Row

print()
print("===== DISCOVERY COVERAGE =====")

tables = [
    ("GitHub", "SELECT COUNT(*) FROM opportunity_verifications"),
    ("Official Sources", "SELECT COUNT(*) FROM official_source_candidates"),
    ("Algora", "SELECT COUNT(*) FROM algora_open_bounties"),
]

for name, sql in tables:
    total = conn.execute(sql).fetchone()[0]
    print(f"{name}: {total}")

print()
print("===== DISCOVERY GAP =====")

targets = {
    "GitHub":500,
    "Official Sources":1000,
    "Algora":500,
}

current = {
    "GitHub":conn.execute("SELECT COUNT(*) FROM opportunity_verifications").fetchone()[0],
    "Official Sources":conn.execute("SELECT COUNT(*) FROM official_source_candidates").fetchone()[0],
    "Algora":conn.execute("SELECT COUNT(*) FROM algora_open_bounties").fetchone()[0],
}

for source in targets:

    gap = max(0,targets[source]-current[source])

    print(
        f"{source}: "
        f"{current[source]} / {targets[source]} "
        f"(faltam {gap})"
    )

print()

total_current = sum(current.values())
total_target = sum(targets.values())

print(f"TOTAL: {total_current} / {total_target}")

conn.close()
