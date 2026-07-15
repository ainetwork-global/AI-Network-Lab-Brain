import sqlite3

conn = sqlite3.connect("11_DATA/global_revenue_brain.db")

conn.execute("""
CREATE TABLE IF NOT EXISTS revenue_execution_history (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    queue_id INTEGER,

    source TEXT,

    title TEXT,

    reward REAL,

    expected_value REAL,

    revenue_per_hour REAL,

    execution_result TEXT,

    actual_revenue REAL,

    execution_time_hours REAL,

    roi REAL,

    notes TEXT,

    executed_at TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

conn.execute("""
CREATE INDEX IF NOT EXISTS idx_execution_result
ON revenue_execution_history(execution_result)
""")

conn.execute("""
CREATE INDEX IF NOT EXISTS idx_execution_roi
ON revenue_execution_history(roi DESC)
""")

conn.commit()

print()
print("===== REVENUE LEARNING LAYER =====")

print(
"Queue:",
conn.execute(
"SELECT COUNT(*) FROM revenue_execution_queue"
).fetchone()[0]
)

print(
"History:",
conn.execute(
"SELECT COUNT(*) FROM revenue_execution_history"
).fetchone()[0]
)

conn.close()
