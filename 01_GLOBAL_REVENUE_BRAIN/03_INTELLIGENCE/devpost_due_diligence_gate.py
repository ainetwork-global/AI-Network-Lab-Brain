from __future__ import annotations

import csv
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "11_DATA" / "global_revenue_brain.db"
CSV_PATH = ROOT / "04_OPPORTUNITIES" / "devpost_due_diligence_queue.csv"
REPORT = ROOT / "12_REPORTS" / "LATEST_DEVPOST_DUE_DILIGENCE.md"

RESTRICTION_TERMS = (
    "high school",
    "student",
    "students",
    "kids",
    "youth",
    "university",
    "college",
    "australia",
    "india",
)

TECHNICAL_FIT_TERMS = (
    "ai",
    "agent",
    "blockchain",
    "x402",
    "api",
    "cloud",
    "database",
    "automation",
    "machine learning",
)

SUSPICIOUS_OR_GENERIC_TERMS = (
    "international hackathon",
    "nexus",
    "global hackathon",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS devpost_due_diligence_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            execution_queue_id INTEGER NOT NULL UNIQUE,
            devpost_hackathon_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            organization TEXT,
            url TEXT NOT NULL,
            submission_url TEXT,
            total_prize_usd REAL,
            participants INTEGER,
            days_remaining INTEGER,
            managed_by_devpost INTEGER,
            invite_only INTEGER,
            cash_prize_count INTEGER,
            anomaly_score REAL,
            identity_confidence REAL,
            technical_fit REAL,
            rule_risk TEXT,
            diligence_status TEXT NOT NULL,
            diligence_reason TEXT,
            human_approval_required INTEGER NOT NULL DEFAULT 1,
            checked_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_devpost_due_status
        ON devpost_due_diligence_queue(
            diligence_status,
            anomaly_score,
            technical_fit DESC
        );
        """
    )
    conn.commit()


def contains_any(text: str, terms: tuple[str, ...]) -> list[str]:
    lowered = text.lower()
    return [term for term in terms if term in lowered]


conn = sqlite3.connect(DATABASE)
conn.row_factory = sqlite3.Row
ensure_table(conn)

rows = conn.execute(
    """
    SELECT
        q.id AS execution_queue_id,
        q.devpost_hackathon_id,
        q.title,
        q.organization,
        q.url,
        q.submission_url,
        q.total_prize_usd,
        q.participants,
        q.days_remaining,
        q.cash_prize_count,
        q.triage_score,
        q.planning_value_per_hour,
        h.managed_by_devpost,
        h.invite_only,
        h.winners_announced,
        h.api_open_state,
        h.skills
    FROM devpost_execution_queue q
    JOIN devpost_hackathons h
      ON h.id = q.devpost_hackathon_id
    WHERE q.triage_status = 'priority_review'
    ORDER BY
        q.planning_value_per_hour DESC,
        q.triage_score DESC
    """
).fetchall()

results = []

print()
print("===== DEVPOST DUE DILIGENCE GATE =====")
print(f"Selecionadas: {len(rows)}")

for row in rows:
    title = row["title"] or ""
    organization = row["organization"] or ""
    combined = f"{title} {organization} {row['skills'] or ''}"

    participants = max(int(row["participants"] or 0), 0)
    prize = float(row["total_prize_usd"] or 0)
    days = row["days_remaining"]

    restrictions = contains_any(combined, RESTRICTION_TERMS)
    fit_terms = contains_any(combined, TECHNICAL_FIT_TERMS)
    generic_terms = contains_any(
        combined,
        SUSPICIOUS_OR_GENERIC_TERMS,
    )

    anomaly_score = 0.0
    reasons = []

    if prize >= 100_000 and participants < 25:
        anomaly_score += 55
        reasons.append(
            "prêmio muito alto com número extremamente baixo de participantes"
        )
    elif prize >= 50_000 and participants < 100:
        anomaly_score += 30
        reasons.append(
            "prêmio elevado com baixa participação"
        )

    if not row["managed_by_devpost"]:
        anomaly_score += 15
        reasons.append(
            "evento não possui selo de gestão direta do Devpost"
        )

    if generic_terms:
        anomaly_score += 10
        reasons.append(
            "nome genérico exige confirmação adicional da organização"
        )

    if restrictions:
        rule_risk = "possible_restriction"
        reasons.append(
            "possível restrição por idade, vínculo ou localização: "
            + ", ".join(restrictions)
        )
    else:
        rule_risk = "rules_not_verified"
        reasons.append(
            "regras completas e elegibilidade internacional ainda não verificadas"
        )

    identity_confidence = 0.45

    if row["managed_by_devpost"]:
        identity_confidence += 0.25

    if participants >= 500:
        identity_confidence += 0.15
    elif participants >= 100:
        identity_confidence += 0.08

    if anomaly_score >= 50:
        identity_confidence -= 0.25

    identity_confidence = round(
        max(0.05, min(0.95, identity_confidence)),
        3,
    )

    technical_fit = round(
        min(0.95, 0.35 + len(fit_terms) * 0.12),
        3,
    )

    if row["invite_only"]:
        status = "rejected"
        reasons.append("evento restrito por convite")

    elif row["winners_announced"]:
        status = "rejected"
        reasons.append("vencedores já anunciados")

    elif row["api_open_state"] != "open":
        status = "rejected"
        reasons.append("evento não está aberto")

    elif anomaly_score >= 50:
        status = "identity_verification_required"

    elif restrictions:
        status = "eligibility_review_required"

    elif identity_confidence < 0.60:
        status = "organization_review_required"

    elif technical_fit < 0.50:
        status = "technical_review_required"

    else:
        status = "rules_review_required"

    reason = "; ".join(dict.fromkeys(reasons))
    checked_at = utc_now()

    conn.execute(
        """
        INSERT INTO devpost_due_diligence_queue (
            execution_queue_id,
            devpost_hackathon_id,
            title,
            organization,
            url,
            submission_url,
            total_prize_usd,
            participants,
            days_remaining,
            managed_by_devpost,
            invite_only,
            cash_prize_count,
            anomaly_score,
            identity_confidence,
            technical_fit,
            rule_risk,
            diligence_status,
            diligence_reason,
            human_approval_required,
            checked_at
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?
        )
        ON CONFLICT(execution_queue_id) DO UPDATE SET
            title = excluded.title,
            organization = excluded.organization,
            url = excluded.url,
            submission_url = excluded.submission_url,
            total_prize_usd = excluded.total_prize_usd,
            participants = excluded.participants,
            days_remaining = excluded.days_remaining,
            managed_by_devpost = excluded.managed_by_devpost,
            invite_only = excluded.invite_only,
            cash_prize_count = excluded.cash_prize_count,
            anomaly_score = excluded.anomaly_score,
            identity_confidence = excluded.identity_confidence,
            technical_fit = excluded.technical_fit,
            rule_risk = excluded.rule_risk,
            diligence_status = excluded.diligence_status,
            diligence_reason = excluded.diligence_reason,
            checked_at = excluded.checked_at
        """,
        (
            row["execution_queue_id"],
            row["devpost_hackathon_id"],
            title,
            organization,
            row["url"],
            row["submission_url"],
            prize,
            participants,
            days,
            int(bool(row["managed_by_devpost"])),
            int(bool(row["invite_only"])),
            int(row["cash_prize_count"] or 0),
            anomaly_score,
            identity_confidence,
            technical_fit,
            rule_risk,
            status,
            reason,
            checked_at,
        ),
    )

    results.append({
        "title": title,
        "organization": organization,
        "url": row["url"],
        "submission_url": row["submission_url"],
        "total_prize_usd": prize,
        "participants": participants,
        "days_remaining": days,
        "managed_by_devpost": int(
            bool(row["managed_by_devpost"])
        ),
        "anomaly_score": anomaly_score,
        "identity_confidence": identity_confidence,
        "technical_fit": technical_fit,
        "rule_risk": rule_risk,
        "diligence_status": status,
        "diligence_reason": reason,
    })

conn.commit()

order = {
    "rules_review_required": 1,
    "eligibility_review_required": 2,
    "technical_review_required": 3,
    "organization_review_required": 4,
    "identity_verification_required": 5,
    "rejected": 6,
}

results.sort(
    key=lambda item: (
        order.get(item["diligence_status"], 9),
        item["anomaly_score"],
        -item["technical_fit"],
    )
)

CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT.parent.mkdir(parents=True, exist_ok=True)

fields = list(results[0].keys()) if results else []

with CSV_PATH.open(
    "w",
    encoding="utf-8-sig",
    newline="",
) as file:
    writer = csv.DictWriter(file, fieldnames=fields)
    writer.writeheader()
    writer.writerows(results)

counts = {}

for item in results:
    status = item["diligence_status"]
    counts[status] = counts.get(status, 0) + 1

lines = [
    "# Devpost Due Diligence Gate",
    "",
    f"Gerado em: {utc_now()}",
    "",
    "Nenhuma submissão ou registro externo foi realizado.",
    "",
    f"- Total analisado: **{len(results)}**",
    f"- Rules review: **{counts.get('rules_review_required', 0)}**",
    f"- Eligibility review: **{counts.get('eligibility_review_required', 0)}**",
    f"- Technical review: **{counts.get('technical_review_required', 0)}**",
    f"- Organization review: **{counts.get('organization_review_required', 0)}**",
    f"- Identity verification: **{counts.get('identity_verification_required', 0)}**",
    f"- Rejected: **{counts.get('rejected', 0)}**",
    "",
]

for index, item in enumerate(results, 1):
    lines.extend([
        f"## {index}. {item['title']}",
        "",
        f"- Organização: {item['organization']}",
        f"- Status: **{item['diligence_status']}**",
        f"- Prêmio total: USD {item['total_prize_usd']:,.2f}",
        f"- Participantes: {item['participants']}",
        f"- Dias restantes: {item['days_remaining']}",
        f"- Gerenciado pelo Devpost: "
        f"{'sim' if item['managed_by_devpost'] else 'não'}",
        f"- Anomaly score: {item['anomaly_score']}",
        f"- Confiança de identidade: "
        f"{item['identity_confidence'] * 100:.1f}%",
        f"- Compatibilidade técnica: "
        f"{item['technical_fit'] * 100:.1f}%",
        f"- Risco de regras: {item['rule_risk']}",
        f"- Motivo: {item['diligence_reason']}",
        f"- URL: {item['url']}",
        "",
    ])

REPORT.write_text("\n".join(lines), encoding="utf-8")

print()
print("===== DEVPOST DUE DILIGENCE SUMMARY =====")
print(f"Analisadas: {len(results)}")
print(
    "Rules review:",
    counts.get("rules_review_required", 0),
)
print(
    "Eligibility review:",
    counts.get("eligibility_review_required", 0),
)
print(
    "Technical review:",
    counts.get("technical_review_required", 0),
)
print(
    "Organization review:",
    counts.get("organization_review_required", 0),
)
print(
    "Identity verification:",
    counts.get("identity_verification_required", 0),
)
print("Rejected:", counts.get("rejected", 0))

print()
print("===== DEVPOST DUE DILIGENCE RESULTS =====")

for index, item in enumerate(results, 1):
    print()
    print(f"{index}. {item['title']}")
    print(f"   status: {item['diligence_status']}")
    print(f"   organização: {item['organization']}")
    print(f"   prêmio: USD {item['total_prize_usd']}")
    print(f"   participantes: {item['participants']}")
    print(f"   anomaly score: {item['anomaly_score']}")
    print(
        f"   confiança de identidade: "
        f"{item['identity_confidence'] * 100:.1f}%"
    )
    print(
        f"   compatibilidade técnica: "
        f"{item['technical_fit'] * 100:.1f}%"
    )
    print(f"   motivo: {item['diligence_reason']}")
    print(f"   url: {item['url']}")

conn.close()
