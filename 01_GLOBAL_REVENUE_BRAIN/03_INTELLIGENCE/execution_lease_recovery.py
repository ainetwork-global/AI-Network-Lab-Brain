import sqlite3
from datetime import datetime, timezone

conn = sqlite3.connect("11_DATA/global_revenue_brain.db")

now = datetime.now(timezone.utc).isoformat()

released = conn.execute("""

UPDATE revenue_execution_tasks

SET
status='pending',
lease_worker=NULL,
lease_until=NULL,
picked_at=NULL

WHERE
status='leased'
AND lease_until IS NOT NULL
AND lease_until < ?

""",(now,)).rowcount

conn.commit()

print()
print("===== EXECUTION LEASE RECOVERY =====")
print("Released:", released)

print()

print("Pending:",
conn.execute(
"SELECT COUNT(*) FROM revenue_execution_tasks WHERE status='pending'"
).fetchone()[0])

print("Leased:",
conn.execute(
"SELECT COUNT(*) FROM revenue_execution_tasks WHERE status='leased'"
).fetchone()[0])

conn.close()
