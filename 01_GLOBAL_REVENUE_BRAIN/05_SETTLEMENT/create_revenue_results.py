import sqlite3

DB="../brain.db"

con=sqlite3.connect(DB)
cur=con.cursor()

cur.execute("""

CREATE TABLE IF NOT EXISTS revenue_results(

id INTEGER PRIMARY KEY AUTOINCREMENT,

opportunity_id INTEGER,

source_name TEXT,

payment_method TEXT,

currency TEXT,

expected_reward REAL,

received_reward REAL,

execution_hours REAL,

status TEXT,

completed_at DATETIME DEFAULT CURRENT_TIMESTAMP

)

""")

con.commit()

print("REVENUE RESULTS TABLE READY")

