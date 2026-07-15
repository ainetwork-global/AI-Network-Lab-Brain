import sqlite3

conn = sqlite3.connect("11_DATA/global_revenue_brain.db")
conn.row_factory = sqlite3.Row

cols = {
    r[1]
    for r in conn.execute(
        "PRAGMA table_info(revenue_execution_tasks)"
    )
}

if "validation_status" not in cols:
    conn.execute("""
    ALTER TABLE revenue_execution_tasks
    ADD COLUMN validation_status TEXT DEFAULT 'pending'
    """)

if "validation_reason" not in cols:
    conn.execute("""
    ALTER TABLE revenue_execution_tasks
    ADD COLUMN validation_reason TEXT
    """)

rows = conn.execute("""

SELECT
t.id,
t.queue_id,
q.source,
q.reward,
q.adaptive_score
FROM revenue_execution_tasks t
JOIN revenue_execution_queue q
ON q.id=t.queue_id

""").fetchall()

approved = 0
review = 0

for row in rows:

    if (
        row["source"]=="algora"
        and row["reward"]>=100
        and row["adaptive_score"]>=70
    ):
        status="approved"
        reason="Atende aos critérios mínimos de execução."
        approved+=1
    else:
        status="manual_review"
        reason="Necessita validação adicional."
        review+=1

    conn.execute("""

    UPDATE revenue_execution_tasks

    SET
    validation_status=?,
    validation_reason=?

    WHERE id=?

    """,(status,reason,row["id"]))

conn.commit()

print()
print("===== EXECUTION VALIDATION =====")
print("Approved:",approved)
print("Manual review:",review)
print("Total:",len(rows))

print()
print("===== APPROVED TASKS =====")

for row in conn.execute("""

SELECT
title,
priority,
validation_status

FROM revenue_execution_tasks

WHERE validation_status='approved'

ORDER BY priority DESC

LIMIT 20

"""):
    print(row)

conn.close()
