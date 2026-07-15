import csv
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path.cwd()
DB = ROOT / "11_DATA" / "global_revenue_brain.db"
CSV_PATH = ROOT / "06_EXECUTION" / "approved_execution_packets.csv"
REPORT_PATH = ROOT / "12_REPORTS" / "LATEST_EXECUTION_PACKETS.md"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

# Libera somente leases de teste que ainda não iniciaram execução real.
released = conn.execute("""
UPDATE revenue_execution_tasks
SET
    status = 'pending',
    lease_worker = NULL,
    lease_until = NULL,
    picked_at = NULL
WHERE status = 'leased'
  AND attempts = 0
  AND started_at IS NULL
  AND finished_at IS NULL
""").rowcount

conn.commit()

rows = conn.execute("""
SELECT
    t.id AS task_id,
    t.title,
    t.priority,
    t.execution_type,
    t.validation_status,
    t.validation_reason,
    q.source,
    q.source_id,
    q.reward,
    q.expected_value,
    q.estimated_hours,
    q.revenue_per_hour,
    q.adaptive_score,
    a.organization,
    a.github_url,
    a.algora_url,
    a.skills,
    a.completion_status
FROM revenue_execution_tasks t
JOIN revenue_execution_queue q
    ON q.id = t.queue_id
LEFT JOIN algora_open_bounties a
    ON q.source = 'algora'
   AND a.id = q.source_id
WHERE t.validation_status = 'approved'
  AND t.status = 'pending'
ORDER BY
    q.revenue_per_hour DESC,
    q.adaptive_score DESC,
    q.reward DESC
LIMIT 20
""").fetchall()

CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

fields = [
    "task_id",
    "title",
    "organization",
    "reward",
    "expected_value",
    "estimated_hours",
    "revenue_per_hour",
    "adaptive_score",
    "skills",
    "github_url",
    "algora_url",
    "completion_status",
    "recommended_action",
    "human_approval_required",
    "execution_status",
]

packets = []

for row in rows:
    if row["github_url"]:
        action = (
            "Revisar integralmente a issue, confirmar que continua aberta, "
            "verificar regras de claim e preparar plano técnico antes de comentar."
        )
    else:
        action = (
            "Abrir a página oficial da bounty, confirmar regras, entregáveis, "
            "prazo e mecanismo de submissão antes de iniciar."
        )

    packets.append({
        "task_id": row["task_id"],
        "title": row["title"],
        "organization": row["organization"] or "não identificada",
        "reward": row["reward"],
        "expected_value": row["expected_value"],
        "estimated_hours": row["estimated_hours"],
        "revenue_per_hour": row["revenue_per_hour"],
        "adaptive_score": row["adaptive_score"],
        "skills": row["skills"] or "não identificadas",
        "github_url": row["github_url"] or "",
        "algora_url": row["algora_url"] or "",
        "completion_status": row["completion_status"] or "não verificado",
        "recommended_action": action,
        "human_approval_required": "sim",
        "execution_status": "dry_run_prepared",
    })

with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=fields)
    writer.writeheader()
    writer.writerows(packets)

lines = [
    "# Global Revenue Brain — Execution Packets",
    "",
    f"Gerado em: {datetime.now(timezone.utc).isoformat()}",
    "",
    "Nenhuma ação externa foi executada.",
    "",
    f"- Leases de teste liberadas: **{released}**",
    f"- Pacotes preparados: **{len(packets)}**",
    "",
]

for index, item in enumerate(packets, 1):
    lines.extend([
        f"## {index}. {item['title']}",
        "",
        f"- Task ID: {item['task_id']}",
        f"- Organização: {item['organization']}",
        f"- Recompensa: USD {item['reward']}",
        f"- Valor esperado: USD {item['expected_value']}",
        f"- Horas estimadas: {item['estimated_hours']}",
        f"- Receita estimada/hora: USD {item['revenue_per_hour']}",
        f"- Adaptive score: {item['adaptive_score']}",
        f"- Competências: {item['skills']}",
        f"- Status da oportunidade: {item['completion_status']}",
        f"- GitHub: {item['github_url'] or 'não identificado'}",
        f"- Algora: {item['algora_url'] or 'não identificado'}",
        f"- Próxima ação: {item['recommended_action']}",
        "- Aprovação humana obrigatória: sim",
        "",
    ])

REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

print()
print("===== EXECUTION PACKET PREPARATION =====")
print("Test leases released:", released)
print("Packets prepared:", len(packets))

print()
print("===== TOP 10 PACKETS =====")

for index, item in enumerate(packets[:10], 1):
    print()
    print(f"{index}. {item['title']}")
    print(f"   task_id: {item['task_id']}")
    print(f"   organização: {item['organization']}")
    print(f"   recompensa: USD {item['reward']}")
    print(f"   receita/hora: USD {item['revenue_per_hour']}")
    print(f"   skills: {item['skills']}")
    print(f"   github: {item['github_url'] or 'não identificado'}")
    print(f"   algora: {item['algora_url'] or 'não identificado'}")

conn.close()
