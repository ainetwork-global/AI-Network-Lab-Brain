import sqlite3

conn = sqlite3.connect("11_DATA/global_revenue_brain.db")

conn.execute("""
CREATE TABLE IF NOT EXISTS revenue_pattern_memory (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    source TEXT,

    category TEXT,

    skill TEXT,

    reward_bucket TEXT,

    success_count INTEGER DEFAULT 0,

    failure_count INTEGER DEFAULT 0,

    total_revenue REAL DEFAULT 0,

    avg_roi REAL DEFAULT 0,

    avg_execution_hours REAL DEFAULT 0,

    last_updated TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

conn.execute("""
CREATE UNIQUE INDEX IF NOT EXISTS idx_pattern_unique
ON revenue_pattern_memory(
    source,
    category,
    skill,
    reward_bucket
)
""")

conn.commit()

print()
print("===== REVENUE PATTERN MEMORY =====")

print(
"Patterns:",
conn.execute(
"SELECT COUNT(*) FROM revenue_pattern_memory"
).fetchone()[0]
)

print(
"History:",
conn.execute(
"SELECT COUNT(*) FROM revenue_execution_history"
).fetchone()[0]
)

conn.close()
