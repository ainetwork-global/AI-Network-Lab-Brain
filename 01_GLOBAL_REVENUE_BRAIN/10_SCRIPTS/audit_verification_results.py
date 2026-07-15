from pathlib import Path
import sqlite3
from datetime import datetime, timezone
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "11_DATA" / "global_revenue_brain.db"
REPORT = ROOT / "12_REPORTS" / "LATEST_VERIFICATION_AUDIT.md"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

rows = conn.execute("""
    SELECT *
    FROM opportunity_verifications
    ORDER BY verification_score DESC
""").fetchall()

def suspicious_reasons(row):
    reasons = []

    title = (row["title"] or "").lower()
    reward = row["reward_amount"]
    currency = row["reward_currency"]
    deadline = row["deadline"]
    requirements = row["requirements"]
    payment = row["payment_method"]
    url = row["url"] or ""
    status = row["verification_status"]

    if reward is not None and reward >= 100000:
        reasons.append("recompensa extremamente alta; confirmar origem do valor")

    if reward is not None and reward < 1:
        reasons.append("recompensa inferior a 1 unidade; pode ser teste ou valor técnico")

    if reward is not None and not currency:
        reasons.append("valor encontrado sem moeda confiável")

    if not deadline:
        reasons.append("prazo não identificado")

    if not requirements:
        reasons.append("requisitos não identificados")

    if not payment:
        reasons.append("forma de pagamento não identificada")

    if status in ("actionable", "approval_required") and not row["explicit_reward"]:
        reasons.append("classificada como prioritária sem recompensa explícita")

    if "issue" in urlparse(url).path.lower():
        if any(term in title for term in [
            "billing", "subscription", "monitor", "discovery",
            "candidates", "claim-to-payout", "test", "canary"
        ]):
            reasons.append("issue técnica pode não representar bounty público executável")

    if row["human_approval_required"] and not row["kyc_required"] and not row["capital_required"]:
        reasons.append("aprovação humana acionada sem motivo sensível claramente registrado")

    return reasons

audited = []
for row in rows:
    reasons = suspicious_reasons(row)
    audited.append((row, reasons))

suspicious = [(row, reasons) for row, reasons in audited if reasons]
cleaner = [(row, reasons) for row, reasons in audited if not reasons]

status_counts = conn.execute("""
    SELECT verification_status, COUNT(*) total
    FROM opportunity_verifications
    GROUP BY verification_status
    ORDER BY total DESC
""").fetchall()

lines = [
    "# Global Revenue Brain — Auditoria da Verificação",
    "",
    f"Gerado em: {datetime.now(timezone.utc).isoformat()}",
    "",
    "## Resumo",
    "",
    f"- Total analisado: **{len(rows)}**",
    f"- Registros suspeitos: **{len(suspicious)}**",
    f"- Registros sem alerta automático: **{len(cleaner)}**",
    "",
    "## Estados",
    ""
]

for item in status_counts:
    lines.append(f"- {item['verification_status']}: **{item['total']}**")

lines.extend([
    "",
    "## Registros que exigem revisão",
    ""
])

for index, (row, reasons) in enumerate(suspicious, 1):
    reward = "não identificada"

    if row["reward_amount"] is not None:
        reward = f"{row['reward_currency'] or '?'} {row['reward_amount']}"

    lines.extend([
        f"### {index}. {row['title']}",
        "",
        f"- Status atual: **{row['verification_status']}**",
        f"- Score: {row['verification_score']}",
        f"- Recompensa interpretada: {reward}",
        f"- Risco: {row['risk_level']}",
        f"- URL: {row['url']}",
        "- Alertas:",
    ])

    for reason in reasons:
        lines.append(f"  - {reason}")

    lines.append("")

lines.extend([
    "## Registros sem alerta automático",
    ""
])

for index, (row, _) in enumerate(cleaner, 1):
    lines.extend([
        f"{index}. **{row['title']}**",
        f"   - Status: {row['verification_status']}",
        f"   - Score: {row['verification_score']}",
        f"   - URL: {row['url']}",
        ""
    ])

REPORT.write_text("\n".join(lines), encoding="utf-8")

print()
print("=== AUDITORIA CONCLUÍDA ===")
print(f"Total analisado: {len(rows)}")
print(f"Suspeitos: {len(suspicious)}")
print(f"Sem alerta automático: {len(cleaner)}")
print(f"Relatório: {REPORT}")

print()
print("=== TOP 20 REGISTROS SUSPEITOS ===")

for index, (row, reasons) in enumerate(suspicious[:20], 1):
    print()
    print(f"{index}. {row['title']}")
    print(f"   status: {row['verification_status']}")
    print(f"   recompensa: {row['reward_currency']} {row['reward_amount']}")
    print(f"   score: {row['verification_score']}")
    print(f"   alertas: {'; '.join(reasons)}")
    print(f"   url: {row['url']}")

conn.close()
