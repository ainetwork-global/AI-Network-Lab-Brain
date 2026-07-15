import sqlite3

conn = sqlite3.connect("11_DATA/global_revenue_brain.db")

conn.execute("""
ALTER TABLE opportunity_verifications
ADD COLUMN origin TEXT
""")
conn.commit()
