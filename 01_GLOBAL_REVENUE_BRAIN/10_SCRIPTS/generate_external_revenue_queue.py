from pathlib import Path
from datetime import datetime, timezone
import csv
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "11_DATA" / "global_revenue_brain.db"
CSV_PATH = ROOT / "04_OPPORTUNITIES" / "external_revenue_queue.csv"
REPORT_PATH = ROOT / "12_REPORTS" / "LATEST_EXTERNAL_REVENUE_QUEUE.md"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

columns = {
    row["name"]
    for row in conn.execute(
        "PRAGMA table_info(opportunity_verifications)"
    ).fetchall()
}

if "origin" not in columns:
    raise RuntimeError("Coluna origin não encontrada.")

rows = conn.execute("""
    SELECT
        opportunity_id,
        title,
        category,
        source,
        url,
        reward_amount,
        reward_currency,
        deadline,
        requirements,
        capital_required,
        difficulty,
        estimated_hours,
        risk_level,
        success_probability,
        verification_score,
        verification_status,
        human_approval_required,
        country_restrictions,
        kyc_required,
        payment_method,
        recommended_action,
        recommendation_reason,
        verified_at
    FROM opportunity_verifications
    WHERE origin = 'external'
      AND verification_status IN (
          'actionable',
          'approval_required',
          'verified'
      )
    ORDER BY
        CASE verification_status
            WHEN 'actionable' THEN 1
            WHEN 'approval_required' THEN 2
            WHEN 'verified' THEN 3
            ELSE 4
        END,
        verification_score DESC,
        success_probability DESC
""").fetchall()

CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

fields = [
    "opportunity_id",
    "title",
    "category",
    "source",
    "url",
    "reward_amount",
    "reward_currency",
    "deadline",
    "requirements",
    "capital_required",
    "difficulty",
    "estimated_hours",
    "risk_level",
    "success_probability",
    "verification_score",
    "verification_status",
    "human_approval_required",
    "country_restrictions",
    "kyc_required",
    "payment_method",
    "recommended_action",
    "recommendation_reason",
    "verified_at",
]

with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=fields)
    writer.writeheader()

    for row in rows:
        writer.writerow({field: row[field] for field in fields})

status_counts = {
    row["verification_status"]: row["total"]
    for row in conn.execute("""
        SELECT verification_status, COUNT(*) AS total
        FROM opportunity_verifications
        WHERE origin = 'external'
        GROUP BY verification_status
    """).fetchall()
}

lines = [
    "# Global Revenue Brain — Fila Externa de Receita",
    "",
    f"Gerado em: {datetime.now(timezone.utc).isoformat()}",
    "",
    "## Resumo",
    "",
    f"- Total externo no banco: **{sum(status_counts.values())}**",
    f"- Fila externa prioritária: **{len(rows)}**",
    f"- Actionable: **{status_counts.get('actionable', 0)}**",
    f"- Approval required: **{status_counts.get('approval_required', 0)}**",
    f"- Verified: **{status_counts.get('verified', 0)}**",
    f"- Rejected: **{status_counts.get('rejected', 0)}**",
    "",
    "## Ranking externo",
    "",
]

if not rows:
    lines.append("Nenhuma oportunidade externa qualificada.")

for index, row in enumerate(rows, 1):
    if row["reward_amount"] is None:
        reward = "não confirmada"
    else:
        reward = (
            f"{row['reward_currency'] or '?'} "
            f"{float(row['reward_amount']):,.2f}"
        )

    probability = float(row["success_probability"] or 0) * 100

    lines.extend([
        f"### {index}. {row['title']}",
        "",
        f"- Status: **{row['verification_status']}**",
        f"- Score: **{row['verification_score']}**",
        f"- Probabilidade estimada: **{probability:.1f}%**",
        f"- Recompensa: **{reward}**",
        f"- Categoria: {row['category'] or 'não classificada'}",
        f"- Fonte: {row['source'] or 'não identificada'}",
        f"- Prazo: {row['deadline'] or 'não identificado'}",
        f"- Dificuldade: {row['difficulty'] or 'não estimada'}",
        f"- Tempo estimado: {row['estimated_hours'] or 'não estimado'} horas",
        f"- Risco: {row['risk_level'] or 'não estimado'}",
        f"- Capital necessário: {'sim' if row['capital_required'] else 'não identificado'}",
        f"- KYC: {'sim' if row['kyc_required'] else 'não identificado'}",
        f"- Aprovação humana: {'sim' if row['human_approval_required'] else 'não'}",
        f"- Forma de pagamento: {row['payment_method'] or 'não identificada'}",
        f"- Próxima ação: **{row['recommended_action']}**",
        f"- Motivo: {row['recommendation_reason']}",
        f"- URL: {row['url']}",
        "",
    ])

REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

print()
print("===== EXTERNAL REVENUE QUEUE =====")
print(f"Total externo: {sum(status_counts.values())}")
print(f"Fila prioritária: {len(rows)}")
print(f"Actionable: {status_counts.get('actionable', 0)}")
print(f"Approval required: {status_counts.get('approval_required', 0)}")
print(f"Verified: {status_counts.get('verified', 0)}")
print(f"Rejected: {status_counts.get('rejected', 0)}")

print()
print("===== TOP 15 EXTERNAL OPPORTUNITIES =====")

for index, row in enumerate(rows[:15], 1):
    reward = (
        f"{row['reward_currency']} {row['reward_amount']}"
        if row["reward_amount"] is not None
        else "não confirmada"
    )

    print()
    print(f"{index}. {row['title']}")
    print(f"   status: {row['verification_status']}")
    print(f"   recompensa: {reward}")
    print(f"   score: {row['verification_score']}")
    print(f"   risco: {row['risk_level']}")
    print(f"   url: {row['url']}")

conn.close()
