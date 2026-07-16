import sqlite3

conn = sqlite3.connect("11_DATA/global_revenue_brain.db")

print()
print("===== OFFICIAL_SOURCE_CANDIDATES SCHEMA =====")

for row in conn.execute("PRAGMA table_info(official_source_candidates)"):
    print(row)

print()
print("===== SAMPLE ROW =====")

cursor = conn.execute("SELECT * FROM official_source_candidates LIMIT 1")

print([d[0] for d in cursor.description])

row = cursor.fetchone()

print(row)

conn.close()
