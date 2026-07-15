import sqlite3
from datetime import datetime, timedelta, timezone
import uuid

WORKER_ID = "brain-worker-" + uuid.uuid4().hex[:8]

conn = sqlite3.connect("11_DATA/global_revenue_brain.db")
conn.row_factory = sqlite3.Row

now = datetime.now(timezone.utc)
lease_until = now + timedelta(minutes=15)

row = conn.execute("""

SELECT id

FROM revenue_execution_tasks

WHERE

status='pending'

AND validation_status='approved'

AND (
lease_until IS NULL
OR lease_until < ?
)

ORDER BY priority DESC

LIMIT 1

""",(now.isoformat(),)).fetchone()

print()
print("===== EXECUTION LEASE TEST =====")

if row is None:

    print("Nenhuma tarefa disponível.")

else:

    conn.execute("""

    UPDATE revenue_execution_tasks

    SET

    lease_worker=?,

    picked_at=?,

    lease_until=?,

    status='leased'

    WHERE id=?

    """,(

        WORKER_ID,

        now.isoformat(),

        lease_until.isoformat(),

        row["id"]

    ))

    conn.commit()

    leased = conn.execute("""

    SELECT

    id,
    title,
    priority,
    lease_worker,
    lease_until

    FROM revenue_execution_tasks

    WHERE id=?

    """,(row["id"],)).fetchone()

    print("Task:", leased["id"])
    print("Title:", leased["title"])
    print("Priority:", leased["priority"])
    print("Worker:", leased["lease_worker"])
    print("Lease until:", leased["lease_until"])

print()

print(
"LEASED:",
conn.execute(
"SELECT COUNT(*) FROM revenue_execution_tasks WHERE status='leased'"
).fetchone()[0]
)

conn.close()
