from __future__ import annotations

import csv
import math
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

DATABASE = (
    ROOT
    / "11_DATA"
    / "global_revenue_brain.db"
)

CSV_PATH = (
    ROOT
    / "04_OPPORTUNITIES"
    / "paid_task_execution_queue.csv"
)

REPORT_PATH = (
    ROOT
    / "12_REPORTS"
    / "LATEST_PAID_TASK_EXECUTION_QUEUE.md"
)


TRADITIONAL_JOB_SOURCES = {
    "arbeitnow",
    "remotive",
    "remoteok",
}


TRADITIONAL_JOB_TERMS = (
    "full-time",
    "full time",
    "permanent",
    "annual salary",
    "yearly salary",
    "employee benefits",
    "health insurance",
    "401k",
    "paid vacation",
    "talent acquisition",
    "customer success manager",
    "product manager",
    "sales specialist",
    "tech lead",
    "medical records manager",
    "years of experience required",
)


TASK_TERMS = {
    "bounty": 30,
    "paid issue": 30,
    "paid task": 30,
    "reward": 22,
    "fixed price": 22,
    "one-time": 20,
    "one time": 20,
    "bug": 20,
    "fix": 18,
    "implement": 18,
    "implementation": 18,
    "script": 24,
    "automation": 28,
    "powershell": 30,
    "python": 26,
    "api": 22,
    "integration": 22,
    "database": 18,
    "sql": 20,
    "data extraction": 24,
    "data processing": 22,
    "web scraping": 18,
    "documentation": 16,
    "technical writing": 16,
    "testing": 18,
    "test": 14,
    "github issue": 22,
    "pull request": 20,
    "frontend fix": 14,
    "backend fix": 18,
    "mcp": 20,
    "agent": 18,
    "workflow": 18,
    "cli": 22,
}


POWERSHELL_FIT_TERMS = {
    "powershell": 1.00,
    "windows": 0.90,
    "script": 0.90,
    "automation": 0.95,
    "cli": 0.90,
    "api": 0.82,
    "json": 0.82,
    "csv": 0.88,
    "database": 0.80,
    "sql": 0.82,
    "github": 0.80,
    "data": 0.76,
    "documentation": 0.70,
    "testing": 0.74,
    "python": 0.90,
    "backend": 0.75,
    "integration": 0.82,
}


HIGH_COMPLEXITY_TERMS = {
    "mobile app": 18,
    "react native": 18,
    "ios": 18,
    "android": 18,
    "rails": 14,
    "kubernetes": 16,
    "smart contract audit": 24,
    "cryptography": 22,
    "machine learning research": 20,
    "pixel art": 18,
    "design system": 14,
    "medical": 18,
}


RISK_TERMS = {
    "deposit required": 100,
    "application fee": 100,
    "purchase required": 100,
    "send crypto": 100,
    "seed phrase": 100,
    "private key": 100,
    "unpaid": 80,
    "volunteer": 60,
    "commission only": 45,
    "equity only": 45,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize(value: object) -> str:
    return re.sub(
        r"\s+",
        " ",
        str(value or ""),
    ).strip().lower()


def table_exists(
    conn: sqlite3.Connection,
    table: str,
) -> bool:
    return bool(
        conn.execute(
            """
            SELECT COUNT(*)
            FROM sqlite_master
            WHERE type='table' AND name=?
            """,
            (table,),
        ).fetchone()[0]
    )


def calculate_term_score(
    text: str,
    mapping: dict[str, int],
) -> tuple[float, list[str]]:
    score = 0.0
    matches: list[str] = []

    for term, weight in mapping.items():
        if term in text:
            score += weight
            matches.append(term)

    return score, matches


def calculate_powershell_fit(
    text: str,
) -> tuple[float, list[str]]:
    matches = [
        (term, value)
        for term, value in POWERSHELL_FIT_TERMS.items()
        if term in text
    ]

    if not matches:
        return 0.20, []

    best = max(value for _, value in matches)

    if len(matches) >= 4:
        best = min(1.0, best + 0.05)

    return round(best, 3), [
        term for term, _ in matches
    ]


def classify_task(
    row: sqlite3.Row,
) -> dict:
    source = normalize(row["source"])
    title = str(row["title"] or "")
    organization = str(row["organization"] or "")
    description = str(row["description"] or "")
    tags = str(row["tags"] or "")
    employment_type = str(row["employment_type"] or "")
    location = str(row["location"] or "")
    url = str(row["url"] or "")

    text = normalize(
        " ".join([
            title,
            description,
            tags,
            employment_type,
            location,
        ])
    )

    is_traditional_source = (
        source in TRADITIONAL_JOB_SOURCES
    )

    traditional_matches = [
        term
        for term in TRADITIONAL_JOB_TERMS
        if term in text
    ]

    task_score, task_matches = (
        calculate_term_score(
            text,
            TASK_TERMS,
        )
    )

    risk_score, risk_matches = (
        calculate_term_score(
            text,
            RISK_TERMS,
        )
    )

    complexity_score, complexity_matches = (
        calculate_term_score(
            text,
            HIGH_COMPLEXITY_TERMS,
        )
    )

    powershell_fit, fit_matches = (
        calculate_powershell_fit(text)
    )

    explicit_payment = bool(
        row["explicit_payment"]
    )

    remote_confirmed = bool(
        row["remote_confirmed"]
    )

    minimum_amount = row["minimum_amount"]
    maximum_amount = row["maximum_amount"]

    amount = (
        maximum_amount
        if maximum_amount is not None
        else minimum_amount
    )

    amount = float(amount or 0)

    is_github_task = (
        source == "github_paid_issues"
    )

    task_like = bool(
        is_github_task
        or task_matches
        or employment_type.lower()
        in {
            "task_or_bounty",
            "project",
            "contract_project",
            "fixed_price",
        }
    )

    traditional_job = bool(
        is_traditional_source
        or traditional_matches
    )

    if is_github_task:
        traditional_job = False

    if risk_score >= 80:
        status = "rejected_risk"
        reason = (
            "Risco incompatível com execução segura: "
            + ", ".join(risk_matches)
        )

    elif traditional_job:
        status = "excluded_traditional_job"
        reason = (
            "Emprego tradicional excluído da estratégia."
        )

    elif not task_like:
        status = "excluded_not_task"
        reason = (
            "Não foi identificada uma tarefa, bounty "
            "ou projeto pontual claramente executável."
        )

    elif not explicit_payment:
        status = "payment_verification_required"
        reason = (
            "Tarefa compatível, mas remuneração explícita "
            "ainda não foi confirmada."
        )

    elif not remote_confirmed:
        status = "remote_verification_required"
        reason = (
            "Pagamento identificado, mas execução remota "
            "ainda não foi confirmada."
        )

    else:
        status = "candidate"

        reasons = [
            "Tarefa pontual identificada.",
            "Remuneração explícita identificada.",
            "Execução remota identificada.",
            (
                "Compatibilidade digital: "
                + ", ".join(fit_matches[:8])
            ),
        ]

        reason = "; ".join(reasons)

    cash_speed = 0.0

    if is_github_task:
        cash_speed += 42

    if "bounty" in text:
        cash_speed += 25

    if "paid issue" in text:
        cash_speed += 25

    if "fixed price" in text:
        cash_speed += 18

    if "one-time" in text or "one time" in text:
        cash_speed += 15

    if explicit_payment:
        cash_speed += 15

    if remote_confirmed:
        cash_speed += 8

    cash_speed = min(100, cash_speed)

    if amount <= 0:
        amount_score = 0
    else:
        amount_score = min(
            25,
            math.log10(amount + 1) * 7,
        )

    estimated_hours = 6.0

    estimated_hours += complexity_score * 0.35

    if powershell_fit >= 0.90:
        estimated_hours -= 2
    elif powershell_fit >= 0.75:
        estimated_hours -= 1

    if "documentation" in text:
        estimated_hours = min(
            estimated_hours,
            8,
        )

    if "script" in text or "automation" in text:
        estimated_hours = min(
            estimated_hours,
            12,
        )

    estimated_hours = round(
        max(1.5, estimated_hours),
        2,
    )

    estimated_value_per_hour = (
        round(amount / estimated_hours, 2)
        if amount > 0
        else 0
    )

    execution_score = (
        task_score * 0.28
        + powershell_fit * 32
        + cash_speed * 0.28
        + amount_score
        - complexity_score * 0.35
        - risk_score
    )

    execution_score = round(
        max(0, min(100, execution_score)),
        2,
    )

    if status == "candidate":
        if (
            execution_score >= 72
            and powershell_fit >= 0.75
            and cash_speed >= 55
        ):
            execution_status = (
                "priority_execution_review"
            )

        elif (
            execution_score >= 52
            and powershell_fit >= 0.60
        ):
            execution_status = (
                "standard_execution_review"
            )

        else:
            execution_status = "low_priority_task"
    else:
        execution_status = status

    return {
        "candidate_key": row["candidate_key"],
        "source": source,
        "title": title,
        "organization": organization,
        "url": url,
        "currency": row["currency"],
        "minimum_amount": minimum_amount,
        "maximum_amount": maximum_amount,
        "expected_amount": amount,
        "payment_evidence": row["payment_evidence"],
        "powershell_fit": powershell_fit,
        "cash_conversion_speed": cash_speed,
        "estimated_hours": estimated_hours,
        "estimated_value_per_hour": (
            estimated_value_per_hour
        ),
        "task_score": round(task_score, 2),
        "execution_score": execution_score,
        "execution_status": execution_status,
        "execution_reason": reason,
        "task_matches": ", ".join(
            task_matches[:12]
        ),
        "fit_matches": ", ".join(
            fit_matches[:12]
        ),
        "complexity_matches": ", ".join(
            complexity_matches[:8]
        ),
        "risk_matches": ", ".join(
            risk_matches[:8]
        ),
    }


conn = sqlite3.connect(DATABASE)
conn.row_factory = sqlite3.Row

if not table_exists(
    conn,
    "paid_work_opportunities",
):
    raise RuntimeError(
        "Tabela paid_work_opportunities não encontrada."
    )

conn.executescript(
    """
    CREATE TABLE IF NOT EXISTS
    paid_task_execution_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        candidate_key TEXT NOT NULL UNIQUE,
        source TEXT NOT NULL,
        title TEXT NOT NULL,
        organization TEXT,
        url TEXT NOT NULL,
        currency TEXT,
        minimum_amount REAL,
        maximum_amount REAL,
        expected_amount REAL,
        payment_evidence TEXT,
        powershell_fit REAL NOT NULL,
        cash_conversion_speed REAL NOT NULL,
        estimated_hours REAL NOT NULL,
        estimated_value_per_hour REAL NOT NULL,
        task_score REAL NOT NULL,
        execution_score REAL NOT NULL,
        execution_status TEXT NOT NULL,
        execution_reason TEXT NOT NULL,
        task_matches TEXT,
        fit_matches TEXT,
        complexity_matches TEXT,
        risk_matches TEXT,
        human_approval_required INTEGER
            NOT NULL DEFAULT 1,
        work_status TEXT
            NOT NULL DEFAULT 'not_started',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS
    idx_paid_task_execution_priority
    ON paid_task_execution_queue(
        execution_status,
        execution_score DESC,
        cash_conversion_speed DESC
    );

    CREATE INDEX IF NOT EXISTS
    idx_paid_task_value_hour
    ON paid_task_execution_queue(
        estimated_value_per_hour DESC
    );
    """
)

rows = conn.execute(
    """
    SELECT *
    FROM paid_work_opportunities
    """
).fetchall()

results = []
now = utc_now()

print()
print("===== PAID TASK EXECUTION FILTER =====")
print("Records analyzed:", len(rows))

for row in rows:
    item = classify_task(row)
    results.append(item)

    conn.execute(
        """
        INSERT INTO paid_task_execution_queue (
            candidate_key,
            source,
            title,
            organization,
            url,
            currency,
            minimum_amount,
            maximum_amount,
            expected_amount,
            payment_evidence,
            powershell_fit,
            cash_conversion_speed,
            estimated_hours,
            estimated_value_per_hour,
            task_score,
            execution_score,
            execution_status,
            execution_reason,
            task_matches,
            fit_matches,
            complexity_matches,
            risk_matches,
            human_approval_required,
            work_status,
            created_at,
            updated_at
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?, 1,
            'not_started', ?, ?
        )
        ON CONFLICT(candidate_key) DO UPDATE SET
            source = excluded.source,
            title = excluded.title,
            organization = excluded.organization,
            url = excluded.url,
            currency = excluded.currency,
            minimum_amount = excluded.minimum_amount,
            maximum_amount = excluded.maximum_amount,
            expected_amount = excluded.expected_amount,
            payment_evidence = excluded.payment_evidence,
            powershell_fit = excluded.powershell_fit,
            cash_conversion_speed =
                excluded.cash_conversion_speed,
            estimated_hours = excluded.estimated_hours,
            estimated_value_per_hour =
                excluded.estimated_value_per_hour,
            task_score = excluded.task_score,
            execution_score = excluded.execution_score,
            execution_status =
                excluded.execution_status,
            execution_reason =
                excluded.execution_reason,
            task_matches = excluded.task_matches,
            fit_matches = excluded.fit_matches,
            complexity_matches =
                excluded.complexity_matches,
            risk_matches = excluded.risk_matches,
            human_approval_required = 1,
            updated_at = excluded.updated_at
        """,
        (
            item["candidate_key"],
            item["source"],
            item["title"],
            item["organization"],
            item["url"],
            item["currency"],
            item["minimum_amount"],
            item["maximum_amount"],
            item["expected_amount"],
            item["payment_evidence"],
            item["powershell_fit"],
            item["cash_conversion_speed"],
            item["estimated_hours"],
            item["estimated_value_per_hour"],
            item["task_score"],
            item["execution_score"],
            item["execution_status"],
            item["execution_reason"],
            item["task_matches"],
            item["fit_matches"],
            item["complexity_matches"],
            item["risk_matches"],
            now,
            now,
        ),
    )

conn.commit()

ranked = conn.execute(
    """
    SELECT *
    FROM paid_task_execution_queue
    WHERE execution_status IN (
        'priority_execution_review',
        'standard_execution_review'
    )
    ORDER BY
        CASE execution_status
            WHEN 'priority_execution_review'
            THEN 1
            ELSE 2
        END,
        execution_score DESC,
        cash_conversion_speed DESC,
        estimated_value_per_hour DESC
    """
).fetchall()

counts = {
    row["execution_status"]: row["total"]
    for row in conn.execute(
        """
        SELECT
            execution_status,
            COUNT(*) AS total
        FROM paid_task_execution_queue
        GROUP BY execution_status
        """
    ).fetchall()
}

CSV_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
)

REPORT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
)

fields = [
    "source",
    "title",
    "organization",
    "url",
    "currency",
    "minimum_amount",
    "maximum_amount",
    "expected_amount",
    "payment_evidence",
    "powershell_fit",
    "cash_conversion_speed",
    "estimated_hours",
    "estimated_value_per_hour",
    "task_score",
    "execution_score",
    "execution_status",
    "execution_reason",
    "task_matches",
    "fit_matches",
    "complexity_matches",
]

with CSV_PATH.open(
    "w",
    encoding="utf-8-sig",
    newline="",
) as file:
    writer = csv.DictWriter(
        file,
        fieldnames=fields,
    )

    writer.writeheader()

    for row in ranked:
        writer.writerow({
            field: row[field]
            for field in fields
        })

lines = [
    "# Global Revenue Brain — Paid Task Execution Queue",
    "",
    f"Gerado em: {utc_now()}",
    "",
    "## Diretriz",
    "",
    "Empregos tradicionais foram excluídos.",
    "",
    "A fila contém apenas tarefas, bounties, issues pagas "
    "e projetos pontuais compatíveis com execução digital.",
    "",
    "Nenhuma candidatura, claim, pull request ou aceite "
    "contratual foi realizado.",
    "",
    "## Resumo",
    "",
    f"- Analisados: **{len(results)}**",
    f"- Priority execution review: "
    f"**{counts.get('priority_execution_review', 0)}**",
    f"- Standard execution review: "
    f"**{counts.get('standard_execution_review', 0)}**",
    f"- Low priority task: "
    f"**{counts.get('low_priority_task', 0)}**",
    f"- Payment verification required: "
    f"**{counts.get('payment_verification_required', 0)}**",
    f"- Empregos tradicionais excluídos: "
    f"**{counts.get('excluded_traditional_job', 0)}**",
    f"- Não classificados como tarefa: "
    f"**{counts.get('excluded_not_task', 0)}**",
    f"- Rejeitados por risco: "
    f"**{counts.get('rejected_risk', 0)}**",
    "",
    "## Ranking",
    "",
]

for index, row in enumerate(
    ranked[:100],
    1,
):
    lines.extend([
        f"### {index}. {row['title']}",
        "",
        f"- Fonte: {row['source']}",
        f"- Solicitante: {row['organization']}",
        f"- Status: **{row['execution_status']}**",
        f"- Score de execução: "
        f"**{row['execution_score']}**",
        f"- Compatibilidade PowerShell/digital: "
        f"**{row['powershell_fit'] * 100:.1f}%**",
        f"- Velocidade de conversão em caixa: "
        f"**{row['cash_conversion_speed']}**",
        f"- Valor esperado: "
        f"{row['currency'] or '?'} "
        f"{row['expected_amount']}",
        f"- Horas estimadas: "
        f"{row['estimated_hours']}",
        f"- Valor estimado/hora: "
        f"{row['currency'] or '?'} "
        f"{row['estimated_value_per_hour']}",
        f"- Evidência de pagamento: "
        f"{row['payment_evidence'] or 'não encontrada'}",
        f"- Capacidades encontradas: "
        f"{row['fit_matches']}",
        f"- Motivo: {row['execution_reason']}",
        f"- URL: {row['url']}",
        "",
    ])

REPORT_PATH.write_text(
    "\n".join(lines),
    encoding="utf-8",
)

print()
print("===== PAID TASK SUMMARY =====")
print(
    "Priority execution review:",
    counts.get(
        "priority_execution_review",
        0,
    ),
)
print(
    "Standard execution review:",
    counts.get(
        "standard_execution_review",
        0,
    ),
)
print(
    "Traditional jobs excluded:",
    counts.get(
        "excluded_traditional_job",
        0,
    ),
)
print(
    "Not task excluded:",
    counts.get(
        "excluded_not_task",
        0,
    ),
)
print(
    "Payment verification required:",
    counts.get(
        "payment_verification_required",
        0,
    ),
)
print(
    "Rejected risk:",
    counts.get(
        "rejected_risk",
        0,
    ),
)

print()
print("===== TOP 20 EXECUTABLE TASKS =====")

for index, row in enumerate(
    ranked[:20],
    1,
):
    print()
    print(
        f"{index}. {row['title']}"
    )
    print(
        f"   source: {row['source']}"
    )
    print(
        f"   requester: {row['organization']}"
    )
    print(
        f"   status: {row['execution_status']}"
    )
    print(
        f"   execution score: "
        f"{row['execution_score']}"
    )
    print(
        f"   powershell fit: "
        f"{row['powershell_fit'] * 100:.1f}%"
    )
    print(
        f"   cash speed: "
        f"{row['cash_conversion_speed']}"
    )
    print(
        f"   expected amount: "
        f"{row['currency']} "
        f"{row['expected_amount']}"
    )
    print(
        f"   estimated hours: "
        f"{row['estimated_hours']}"
    )
    print(
        f"   value/hour: "
        f"{row['estimated_value_per_hour']}"
    )
    print(
        f"   url: {row['url']}"
    )

conn.close()
