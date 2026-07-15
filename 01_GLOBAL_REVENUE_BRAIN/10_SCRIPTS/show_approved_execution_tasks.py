import sqlite3

conn = sqlite3.connect("11_DATA/global_revenue_brain.db")
conn.row_factory = sqlite3.Row

print()
print("===== APPROVED EXECUTION TASKS =====")

rows = conn.execute("""
SELECT
    t.id AS task_id,
    t.title,
    t.priority,
    t.execution_type,
    t.validation_status,
    q.reward,
    q.expected_value,
    q.estimated_hours,
    q.revenue_per_hour,
    a.organization,
    a.github_url,
    a.algora_url,
    a.completion_status
FROM revenue_execution_tasks t
JOIN revenue_execution_queue q
    ON q.id = t.queue_id
LEFT JOIN algora_open_bounties a
    ON q.source = 'algora'
   AND a.id = q.source_id
WHERE t.validation_status = 'approved'
ORDER BY
    t.priority DESC,
    q.revenue_per_hour DESC,
    q.reward DESC
""").fetchall()

for index, row in enumerate(rows, 1):
    print()
    print(f"{index}. {row['title']}")
    print(f"   task_id: {row['task_id']}")
    print(f"   organização: {row['organization'] or 'não identificada'}")
    print(f"   recompensa: USD {row['reward']}")
    print(f"   valor esperado: USD {row['expected_value']}")
    print(f"   horas estimadas: {row['estimated_hours']}")
    print(f"   receita estimada/hora: USD {row['revenue_per_hour']}")
    print(f"   prioridade: {row['priority']}")
    print(f"   status da bounty: {row['completion_status'] or 'não verificado'}")
    print(f"   github: {row['github_url'] or 'não identificado'}")
    print(f"   algora: {row['algora_url'] or 'não identificado'}")

print()
print(f"TOTAL APPROVED: {len(rows)}")

conn.close()
