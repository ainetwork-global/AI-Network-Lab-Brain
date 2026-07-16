from __future__ import annotations

import csv
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "11_DATA" / "global_revenue_brain.db"
CSV_PATH = ROOT / "04_OPPORTUNITIES" / "devpost_execution_triage.csv"
REPORT = ROOT / "12_REPORTS" / "LATEST_DEVPOST_EXECUTION_TRIAGE.md"

HIGH_FIT_TERMS = (
    "machine learning",
    "artificial intelligence",
    "agent",
    "automation",
    "api",
    "cloud",
    "database",
    "devops",
    "productivity",
    "fintech",
    "blockchain",
)

LOW_FIT_TERMS = (
    "high school",
    "kids",
    "student only",
    "university students only",
    "pitch competition",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def days_remaining(end_date: str | None) -> int | None:
    if not end_date:
        return None

    try:
        deadline = datetime.fromisoformat(end_date).date()
        return (deadline - datetime.now(timezone.utc).date()).days
    except ValueError:
        return None


def calculate_theme_fit(title: str, skills: str) -> tuple[float, str]:
    combined = f"{title} {skills}".lower()
    fit = 0.45
    reasons = []

    positive = [
        term for term in HIGH_FIT_TERMS
        if term in combined
    ]

    negative = [
        term for term in LOW_FIT_TERMS
        if term in combined
    ]

    if positive:
        fit += min(0.40, len(positive) * 0.10)
        reasons.append(
            "compatibilidade: " + ", ".join(positive[:5])
        )

    if negative:
        fit -= min(0.40, len(negative) * 0.18)
        reasons.append(
            "restrição provável: " + ", ".join(negative[:5])
        )

    return (
        round(max(0.05, min(0.95, fit)), 4),
        "; ".join(reasons),
    )


def calculate_competition(participants: int) -> float:
    return round(
        max(
            0.02,
            min(0.75, 3.0 / math.sqrt(max(participants, 1))),
        ),
        5,
    )


def calculate_deadline_factor(days: int | None) -> float:
    if days is None:
        return 0.20
    if days < 0:
        return 0.0
    if days < 4:
        return 0.10
    if days < 7:
        return 0.25
    if days < 14:
        return 0.60
    if days <= 45:
        return 1.0
    return 0.85


def estimate_hours(
    prize: float,
    participants: int,
    fit: float,
) -> float:
    hours = 30.0

    if prize >= 100_000:
        hours += 90
    elif prize >= 20_000:
        hours += 60
    elif prize >= 5_000:
        hours += 35
    else:
        hours += 15

    if participants >= 10_000:
        hours += 50
    elif participants >= 2_000:
        hours += 25

    if fit < 0.50:
        hours += 25

    return hours


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS devpost_execution_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            devpost_hackathon_id INTEGER NOT NULL UNIQUE,
            title TEXT NOT NULL,
            organization TEXT,
            url TEXT NOT NULL,
            submission_url TEXT,
            total_prize_usd REAL,
            cash_prize_count INTEGER,
            estimated_prize_share_usd REAL,
            participants INTEGER,
            days_remaining INTEGER,
            theme_fit REAL,
            competition_factor REAL,
            deadline_factor REAL,
            estimated_hours REAL,
            planning_probability REAL,
            planning_value_usd REAL,
            planning_value_per_hour REAL,
            triage_score REAL,
            triage_status TEXT NOT NULL,
            triage_reason TEXT,
            eligibility_status TEXT NOT NULL,
            human_approval_required INTEGER NOT NULL DEFAULT 1,
            execution_status TEXT NOT NULL DEFAULT 'not_started',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_devpost_triage_status
        ON devpost_execution_queue(
            triage_status,
            triage_score DESC
        );
        """
    )
    conn.commit()


conn = sqlite3.connect(DATABASE)
conn.row_factory = sqlite3.Row
ensure_table(conn)

rows = conn.execute(
    """
    SELECT
        id,
        title,
        organization,
        url,
        start_submission_url,
        reward_amount,
        cash_prize_count,
        participants,
        end_date,
        skills,
        invite_only,
        winners_announced,
        api_open_state
    FROM devpost_hackathons
    WHERE api_truth_status = 'api_actionable'
    ORDER BY reward_amount DESC
    """
).fetchall()

results = []

print()
print("===== DEVPOST EXECUTION TRIAGE =====")
print(f"Selecionadas: {len(rows)}")

for row in rows:
    prize = float(row["reward_amount"] or 0)
    prize_count = max(int(row["cash_prize_count"] or 1), 1)
    participants = max(int(row["participants"] or 1), 1)
    days = days_remaining(row["end_date"])

    fit, fit_reason = calculate_theme_fit(
        row["title"] or "",
        row["skills"] or "",
    )

    competition = calculate_competition(participants)
    deadline = calculate_deadline_factor(days)
    estimated_share = prize / prize_count

    hours = estimate_hours(
        prize,
        participants,
        fit,
    )

    probability = round(
        max(
            0.001,
            min(
                0.20,
                fit * competition * deadline * 0.30,
            ),
        ),
        5,
    )

    planning_value = round(
        estimated_share * probability,
        2,
    )

    value_per_hour = round(
        planning_value / max(hours, 1),
        2,
    )

    score = (
        fit * 35
        + competition * 25
        + deadline * 20
        + min(20, math.log10(max(prize, 1)) * 4)
    )

    reasons = [
        fit_reason,
        f"{participants} participantes",
        f"{prize_count} faixas de prêmio",
        f"{days if days is not None else 'prazo desconhecido'} dias restantes",
        "regras e elegibilidade ainda exigem revisão humana",
    ]

    if row["invite_only"]:
        status = "rejected"
        score = 0
        reasons.append("evento restrito por convite")

    elif row["winners_announced"]:
        status = "rejected"
        score = 0
        reasons.append("vencedores já anunciados")

    elif row["api_open_state"] != "open":
        status = "rejected"
        score = 0
        reasons.append("evento não está aberto")

    elif days is None or days < 7:
        status = "manual_review"
        reasons.append("prazo ausente ou curto")

    elif fit < 0.45:
        status = "manual_review"
        reasons.append("baixa compatibilidade técnica")

    elif value_per_hour >= 2 and score >= 55:
        status = "priority_review"

    elif value_per_hour >= 0.50:
        status = "standard_review"

    else:
        status = "low_priority"

    score = round(max(0, min(100, score)), 2)
    now = utc_now()

    reason = "; ".join(
        item
        for item in dict.fromkeys(reasons)
        if item
    )

    conn.execute(
        """
        INSERT INTO devpost_execution_queue (
            devpost_hackathon_id,
            title,
            organization,
            url,
            submission_url,
            total_prize_usd,
            cash_prize_count,
            estimated_prize_share_usd,
            participants,
            days_remaining,
            theme_fit,
            competition_factor,
            deadline_factor,
            estimated_hours,
            planning_probability,
            planning_value_usd,
            planning_value_per_hour,
            triage_score,
            triage_status,
            triage_reason,
            eligibility_status,
            human_approval_required,
            execution_status,
            created_at,
            updated_at
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, 'manual_rules_review', 1,
            'not_started', ?, ?
        )
        ON CONFLICT(devpost_hackathon_id) DO UPDATE SET
            title = excluded.title,
            organization = excluded.organization,
            url = excluded.url,
            submission_url = excluded.submission_url,
            total_prize_usd = excluded.total_prize_usd,
            cash_prize_count = excluded.cash_prize_count,
            estimated_prize_share_usd =
                excluded.estimated_prize_share_usd,
            participants = excluded.participants,
            days_remaining = excluded.days_remaining,
            theme_fit = excluded.theme_fit,
            competition_factor = excluded.competition_factor,
            deadline_factor = excluded.deadline_factor,
            estimated_hours = excluded.estimated_hours,
            planning_probability = excluded.planning_probability,
            planning_value_usd = excluded.planning_value_usd,
            planning_value_per_hour =
                excluded.planning_value_per_hour,
            triage_score = excluded.triage_score,
            triage_status = excluded.triage_status,
            triage_reason = excluded.triage_reason,
            updated_at = excluded.updated_at
        """,
        (
            row["id"],
            row["title"],
            row["organization"],
            row["url"],
            row["start_submission_url"],
            prize,
            prize_count,
            round(estimated_share, 2),
            participants,
            days,
            fit,
            competition,
            deadline,
            hours,
            probability,
            planning_value,
            value_per_hour,
            score,
            status,
            reason,
            now,
            now,
        ),
    )

    results.append({
        "title": row["title"],
        "organization": row["organization"],
        "url": row["url"],
        "submission_url": row["start_submission_url"],
        "total_prize_usd": prize,
        "estimated_prize_share_usd": round(estimated_share, 2),
        "participants": participants,
        "days_remaining": days,
        "estimated_hours": hours,
        "planning_probability": probability,
        "planning_value_usd": planning_value,
        "planning_value_per_hour": value_per_hour,
        "triage_score": score,
        "triage_status": status,
        "triage_reason": reason,
    })

conn.commit()

order = {
    "priority_review": 1,
    "standard_review": 2,
    "manual_review": 3,
    "low_priority": 4,
    "rejected": 5,
}

results.sort(
    key=lambda item: (
        order.get(item["triage_status"], 9),
        -item["planning_value_per_hour"],
        -item["triage_score"],
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
    status = item["triage_status"]
    counts[status] = counts.get(status, 0) + 1

lines = [
    "# Devpost Execution Triage",
    "",
    f"Gerado em: {utc_now()}",
    "",
    "Valores usados apenas para planejamento, sem garantia de receita.",
    "",
    f"- Analisadas: **{len(results)}**",
    f"- Priority review: **{counts.get('priority_review', 0)}**",
    f"- Standard review: **{counts.get('standard_review', 0)}**",
    f"- Manual review: **{counts.get('manual_review', 0)}**",
    f"- Low priority: **{counts.get('low_priority', 0)}**",
    f"- Rejected: **{counts.get('rejected', 0)}**",
    "",
]

for index, item in enumerate(results, 1):
    lines.extend([
        f"## {index}. {item['title']}",
        "",
        f"- Status: {item['triage_status']}",
        f"- Prêmio total: USD {item['total_prize_usd']:,.2f}",
        f"- Prêmio médio: USD {item['estimated_prize_share_usd']:,.2f}",
        f"- Participantes: {item['participants']}",
        f"- Dias restantes: {item['days_remaining']}",
        f"- Horas estimadas: {item['estimated_hours']}",
        f"- Probabilidade de planejamento: "
        f"{item['planning_probability'] * 100:.3f}%",
        f"- Valor/hora: USD {item['planning_value_per_hour']:,.2f}",
        f"- Score: {item['triage_score']}",
        f"- Motivo: {item['triage_reason']}",
        f"- URL: {item['url']}",
        "",
    ])

REPORT.write_text("\n".join(lines), encoding="utf-8")

print()
print("===== DEVPOST TRIAGE SUMMARY =====")
print(f"Analisadas: {len(results)}")
print(f"Priority review: {counts.get('priority_review', 0)}")
print(f"Standard review: {counts.get('standard_review', 0)}")
print(f"Manual review: {counts.get('manual_review', 0)}")
print(f"Low priority: {counts.get('low_priority', 0)}")
print(f"Rejected: {counts.get('rejected', 0)}")

print()
print("===== TOP 15 DEVPOST TRIAGE =====")

for index, item in enumerate(results[:15], 1):
    print()
    print(f"{index}. {item['title']}")
    print(f"   status: {item['triage_status']}")
    print(f"   prêmio total: USD {item['total_prize_usd']}")
    print(f"   participantes: {item['participants']}")
    print(f"   dias restantes: {item['days_remaining']}")
    print(
        f"   probabilidade: "
        f"{item['planning_probability'] * 100:.3f}%"
    )
    print(
        f"   valor/hora: "
        f"USD {item['planning_value_per_hour']}"
    )
    print(f"   score: {item['triage_score']}")
    print(f"   url: {item['url']}")

conn.close()
