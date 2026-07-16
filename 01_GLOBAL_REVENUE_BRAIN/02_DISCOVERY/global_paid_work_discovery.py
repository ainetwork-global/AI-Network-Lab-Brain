from __future__ import annotations

import csv
import hashlib
import html
import json
import os
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]

DATABASE = (
    ROOT
    / "11_DATA"
    / "global_revenue_brain.db"
)

CSV_PATH = (
    ROOT
    / "04_OPPORTUNITIES"
    / "global_paid_work_candidates.csv"
)

REPORT_PATH = (
    ROOT
    / "12_REPORTS"
    / "LATEST_GLOBAL_PAID_WORK_DISCOVERY.md"
)

ERROR_LOG = (
    ROOT
    / "09_LOGS"
    / "global_paid_work_discovery_errors.log"
)

HEADERS = {
    "User-Agent": (
        "GlobalRevenueBrain/2.0 "
        "(authorized public opportunity discovery)"
    ),
    "Accept": "application/json",
}

GITHUB_TOKEN = os.getenv(
    "GITHUB_TOKEN",
    "",
).strip()

if GITHUB_TOKEN:
    HEADERS["Authorization"] = (
        f"Bearer {GITHUB_TOKEN}"
    )


SOURCE_URLS = {
    "arbeitnow": (
        "https://www.arbeitnow.com/"
        "api/job-board-api"
    ),
    "remotive": (
        "https://remotive.com/"
        "api/remote-jobs"
    ),
    "remoteok": (
        "https://remoteok.com/api"
    ),
    "github_search": (
        "https://api.github.com/"
        "search/issues"
    ),
}


GITHUB_QUERIES = (
    (
        'is:issue is:open '
        '(bounty OR reward) '
        '(python OR powershell OR automation)'
    ),
    (
        'is:issue is:open '
        '"paid task" '
        '(api OR script OR integration)'
    ),
    (
        'is:issue is:open '
        '"$" bounty '
        '(documentation OR data OR testing)'
    ),
    (
        'is:issue is:open '
        '(USDC OR USD) '
        '(bounty OR paid) '
        '-label:invalid'
    ),
    (
        'is:issue is:open '
        '"help wanted" '
        '(bounty OR payment OR reward)'
    ),
)


CAPABILITY_TERMS = {
    "powershell": 25,
    "python": 22,
    "automation": 24,
    "api": 20,
    "integration": 18,
    "scripting": 20,
    "script": 18,
    "data processing": 20,
    "data extraction": 22,
    "web scraping": 16,
    "database": 16,
    "sql": 18,
    "documentation": 14,
    "technical writing": 16,
    "testing": 15,
    "qa": 13,
    "ai": 16,
    "llm": 18,
    "agent": 18,
    "workflow": 16,
    "github": 12,
    "devops": 15,
    "backend": 14,
    "fastapi": 20,
}


WORK_TERMS = {
    "contract": 16,
    "contractor": 18,
    "freelance": 22,
    "project-based": 22,
    "project based": 22,
    "fixed price": 22,
    "one-time": 18,
    "one time": 18,
    "temporary": 10,
    "part-time": 10,
    "part time": 10,
    "consultant": 14,
    "consulting": 14,
    "paid task": 28,
    "bounty": 25,
    "reward": 20,
    "commission": 12,
}


PAYMENT_TERMS = {
    "salary": 14,
    "compensation": 18,
    "paid": 16,
    "payment": 16,
    "budget": 18,
    "bounty": 22,
    "reward": 20,
    "usd": 14,
    "usdc": 16,
    "$": 10,
    "€": 10,
    "eur": 12,
    "hourly": 16,
    "per hour": 16,
    "fixed price": 18,
}


REMOTE_TERMS = {
    "worldwide": 18,
    "anywhere": 18,
    "global": 12,
    "remote": 16,
    "work from home": 14,
    "distributed": 10,
    "async": 10,
    "contract": 8,
}


NEGATIVE_TERMS = {
    "unpaid": -60,
    "volunteer": -45,
    "equity only": -45,
    "commission only": -35,
    "must be located in": -12,
    "security clearance required": -30,
    "on-site only": -40,
    "onsite only": -40,
    "internship unpaid": -60,
    "pay to apply": -100,
    "application fee": -50,
    "deposit required": -100,
    "purchase required": -80,
    "send crypto": -100,
    "seed phrase": -100,
    "private key": -100,
}


AUTOMATABLE_TERMS = {
    "powershell": 1.0,
    "python": 1.0,
    "script": 0.95,
    "automation": 1.0,
    "api": 0.90,
    "integration": 0.85,
    "data": 0.80,
    "documentation": 0.70,
    "testing": 0.75,
    "research": 0.65,
    "analysis": 0.70,
    "backend": 0.80,
    "devops": 0.75,
}


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def clean(value: Any) -> str:
    text = html.unescape(
        str(value or "")
    )

    text = re.sub(
        r"<[^>]+>",
        " ",
        text,
    )

    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


def log_error(
    source: str,
    error: Exception,
) -> None:
    ERROR_LOG.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with ERROR_LOG.open(
        "a",
        encoding="utf-8",
    ) as file:
        file.write(
            f"{utc_now()} | "
            f"{source} | "
            f"{type(error).__name__} | "
            f"{error}\n"
        )


def stable_key(
    source: str,
    external_id: str,
    url: str,
    title: str,
) -> str:
    raw = (
        f"{source}|"
        f"{external_id}|"
        f"{url}|"
        f"{title}"
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


def parse_amounts(
    text: str,
) -> tuple[
    float | None,
    float | None,
    str | None,
    str | None,
]:
    patterns = (
        re.compile(
            r"(?:US\$|USD|\$)\s*"
            r"(\d[\d,.]*)"
            r"(?:\s*[-–]\s*"
            r"(?:US\$|USD|\$)?\s*"
            r"(\d[\d,.]*))?",
            re.I,
        ),
        re.compile(
            r"(?:EUR|€)\s*"
            r"(\d[\d,.]*)"
            r"(?:\s*[-–]\s*"
            r"(?:EUR|€)?\s*"
            r"(\d[\d,.]*))?",
            re.I,
        ),
        re.compile(
            r"(?:USDC)\s*"
            r"(\d[\d,.]*)"
            r"(?:\s*[-–]\s*"
            r"(?:USDC)?\s*"
            r"(\d[\d,.]*))?",
            re.I,
        ),
    )

    for pattern in patterns:
        match = pattern.search(text)

        if not match:
            continue

        values = []

        for raw in match.groups():
            if not raw:
                continue

            try:
                values.append(
                    float(
                        raw.replace(",", "")
                    )
                )
            except ValueError:
                pass

        if not values:
            continue

        evidence = clean(
            match.group(0)
        )

        if "€" in evidence or "EUR" in evidence.upper():
            currency = "EUR"
        elif "USDC" in evidence.upper():
            currency = "USDC"
        else:
            currency = "USD"

        return (
            min(values),
            max(values),
            currency,
            evidence,
        )

    return None, None, None, None


def term_score(
    text: str,
    mapping: dict[str, int],
) -> tuple[float, list[str]]:
    score = 0.0
    matches = []

    for term, weight in mapping.items():
        if term in text:
            score += weight
            matches.append(term)

    return score, matches


def calculate_automation_fit(
    text: str,
) -> tuple[float, list[str]]:
    matches = [
        (
            term,
            value,
        )
        for term, value
        in AUTOMATABLE_TERMS.items()
        if term in text
    ]

    if not matches:
        return 0.25, []

    fit = max(
        value
        for _, value in matches
    )

    return fit, [
        term
        for term, _ in matches
    ]


def classify(
    item: dict[str, Any],
) -> dict[str, Any]:
    combined = clean(
        " ".join([
            item.get("title", ""),
            item.get("description", ""),
            item.get("tags", ""),
            item.get("location", ""),
            item.get("employment_type", ""),
        ])
    ).lower()

    capability_score, capabilities = (
        term_score(
            combined,
            CAPABILITY_TERMS,
        )
    )

    work_score, work_matches = (
        term_score(
            combined,
            WORK_TERMS,
        )
    )

    payment_score, payment_matches = (
        term_score(
            combined,
            PAYMENT_TERMS,
        )
    )

    remote_score, remote_matches = (
        term_score(
            combined,
            REMOTE_TERMS,
        )
    )

    negative_score, negative_matches = (
        term_score(
            combined,
            NEGATIVE_TERMS,
        )
    )

    (
        min_amount,
        max_amount,
        currency,
        payment_evidence,
    ) = parse_amounts(combined)

    automation_fit, automation_matches = (
        calculate_automation_fit(
            combined
        )
    )

    explicit_payment = bool(
        payment_evidence
        or payment_matches
        or item.get("salary")
    )

    remote_confirmed = bool(
        item.get("remote")
        or remote_matches
        or "worldwide" in combined
    )

    direct_task = bool(
        work_matches
        or item["source"]
        == "github_paid_issues"
    )

    score = 15.0

    score += min(
        capability_score,
        35,
    )

    score += min(
        work_score,
        25,
    )

    score += min(
        payment_score,
        20,
    )

    score += min(
        remote_score,
        15,
    )

    score += automation_fit * 20
    score += negative_score

    if explicit_payment:
        score += 12
    else:
        score -= 20

    if remote_confirmed:
        score += 10
    else:
        score -= 12

    if direct_task:
        score += 8

    if min_amount is not None:
        score += 5

    score = round(
        max(0, min(100, score)),
        2,
    )

    if negative_score <= -80:
        status = "rejected"
    elif (
        score >= 72
        and explicit_payment
        and remote_confirmed
        and automation_fit >= 0.65
    ):
        status = "actionable_review"
    elif (
        score >= 52
        and automation_fit >= 0.50
    ):
        status = "manual_review"
    else:
        status = "low_priority"

    if item["source"] == "github_paid_issues":
        application_type = "claim_or_proposal"
    elif direct_task:
        application_type = "proposal_or_application"
    else:
        application_type = "job_application"

    reasons = []

    if capabilities:
        reasons.append(
            "Capacidades compatíveis: "
            + ", ".join(
                capabilities[:8]
            )
        )

    if automation_matches:
        reasons.append(
            "Executável digitalmente: "
            + ", ".join(
                automation_matches[:8]
            )
        )

    if explicit_payment:
        reasons.append(
            "Indício explícito de remuneração."
        )
    else:
        reasons.append(
            "Remuneração não confirmada."
        )

    if remote_confirmed:
        reasons.append(
            "Execução remota identificada."
        )
    else:
        reasons.append(
            "Execução remota não confirmada."
        )

    if negative_matches:
        reasons.append(
            "Riscos encontrados: "
            + ", ".join(
                negative_matches
            )
        )

    return {
        **item,
        "minimum_amount": min_amount,
        "maximum_amount": max_amount,
        "currency": (
            currency
            or item.get("currency")
        ),
        "payment_evidence": (
            payment_evidence
            or item.get("salary")
        ),
        "explicit_payment": int(
            explicit_payment
        ),
        "remote_confirmed": int(
            remote_confirmed
        ),
        "automation_fit": round(
            automation_fit,
            3,
        ),
        "application_type": (
            application_type
        ),
        "discovery_score": score,
        "discovery_status": status,
        "discovery_reason": (
            "; ".join(reasons)
        ),
    }


def fetch_arbeitnow() -> list[dict[str, Any]]:
    results = []

    for page in range(1, 6):
        response = requests.get(
            SOURCE_URLS["arbeitnow"],
            params={"page": page},
            headers=HEADERS,
            timeout=30,
        )

        response.raise_for_status()
        payload = response.json()

        rows = payload.get("data") or []

        if not rows:
            break

        for row in rows:
            tags = row.get("tags") or []

            results.append({
                "source": "arbeitnow",
                "external_id": str(
                    row.get("slug")
                    or row.get("id")
                    or ""
                ),
                "title": clean(
                    row.get("title")
                ),
                "organization": clean(
                    row.get("company_name")
                ),
                "description": clean(
                    row.get("description")
                ),
                "url": clean(
                    row.get("url")
                ),
                "location": clean(
                    row.get("location")
                ),
                "remote": int(
                    bool(row.get("remote"))
                ),
                "tags": clean(
                    ", ".join(tags)
                ),
                "employment_type": clean(
                    row.get("job_types")
                ),
                "salary": "",
                "published_at": clean(
                    row.get("created_at")
                ),
            })

    return results


def fetch_remotive() -> list[dict[str, Any]]:
    response = requests.get(
        SOURCE_URLS["remotive"],
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()
    payload = response.json()

    results = []

    for row in (
        payload.get("jobs")
        or []
    )[:500]:
        results.append({
            "source": "remotive",
            "external_id": str(
                row.get("id") or ""
            ),
            "title": clean(
                row.get("title")
            ),
            "organization": clean(
                row.get("company_name")
            ),
            "description": clean(
                row.get("description")
            ),
            "url": clean(
                row.get("url")
            ),
            "location": clean(
                row.get(
                    "candidate_required_location"
                )
            ),
            "remote": 1,
            "tags": clean(
                row.get("category")
            ),
            "employment_type": clean(
                row.get("job_type")
            ),
            "salary": clean(
                row.get("salary")
            ),
            "published_at": clean(
                row.get("publication_date")
            ),
        })

    return results


def fetch_remoteok() -> list[dict[str, Any]]:
    response = requests.get(
        SOURCE_URLS["remoteok"],
        headers={
            **HEADERS,
            "User-Agent": (
                "Mozilla/5.0 "
                "GlobalRevenueBrain/2.0"
            ),
        },
        timeout=30,
    )

    response.raise_for_status()
    payload = response.json()

    results = []

    for row in payload:
        if not isinstance(row, dict):
            continue

        if not row.get("position"):
            continue

        salary_min = row.get("salary_min")
        salary_max = row.get("salary_max")

        salary_parts = []

        if salary_min:
            salary_parts.append(
                f"USD {salary_min}"
            )

        if salary_max:
            salary_parts.append(
                f"USD {salary_max}"
            )

        results.append({
            "source": "remoteok",
            "external_id": str(
                row.get("id") or ""
            ),
            "title": clean(
                row.get("position")
            ),
            "organization": clean(
                row.get("company")
            ),
            "description": clean(
                row.get("description")
            ),
            "url": clean(
                row.get("url")
                or row.get("apply_url")
            ),
            "location": clean(
                row.get("location")
                or "Worldwide"
            ),
            "remote": 1,
            "tags": clean(
                ", ".join(
                    row.get("tags") or []
                )
            ),
            "employment_type": (
                "remote"
            ),
            "salary": " - ".join(
                salary_parts
            ),
            "published_at": clean(
                row.get("date")
            ),
        })

    return results


def fetch_github_paid_issues() -> list[dict[str, Any]]:
    results = []
    seen_urls = set()

    for query in GITHUB_QUERIES:
        response = requests.get(
            SOURCE_URLS["github_search"],
            params={
                "q": query,
                "sort": "updated",
                "order": "desc",
                "per_page": 50,
            },
            headers=HEADERS,
            timeout=30,
        )

        response.raise_for_status()
        payload = response.json()

        for row in (
            payload.get("items")
            or []
        ):
            url = clean(
                row.get("html_url")
            )

            if not url or url in seen_urls:
                continue

            seen_urls.add(url)

            labels = []

            for label in (
                row.get("labels")
                or []
            ):
                if isinstance(label, dict):
                    labels.append(
                        clean(
                            label.get("name")
                        )
                    )

            repository_url = clean(
                row.get("repository_url")
            )

            repository = (
                repository_url
                .replace(
                    "https://api.github.com/repos/",
                    "",
                )
            )

            results.append({
                "source": "github_paid_issues",
                "external_id": str(
                    row.get("id") or ""
                ),
                "title": clean(
                    row.get("title")
                ),
                "organization": repository,
                "description": clean(
                    row.get("body")
                ),
                "url": url,
                "location": "Online",
                "remote": 1,
                "tags": clean(
                    ", ".join(labels)
                ),
                "employment_type": (
                    "task_or_bounty"
                ),
                "salary": "",
                "published_at": clean(
                    row.get("created_at")
                ),
            })

        time.sleep(1)

    return results


def ensure_schema(
    conn: sqlite3.Connection,
) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS
        paid_work_opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_key TEXT NOT NULL UNIQUE,
            source TEXT NOT NULL,
            external_id TEXT,
            title TEXT NOT NULL,
            organization TEXT,
            description TEXT,
            url TEXT NOT NULL,
            location TEXT,
            remote INTEGER NOT NULL DEFAULT 0,
            tags TEXT,
            employment_type TEXT,
            salary TEXT,
            minimum_amount REAL,
            maximum_amount REAL,
            currency TEXT,
            payment_evidence TEXT,
            explicit_payment INTEGER
                NOT NULL DEFAULT 0,
            remote_confirmed INTEGER
                NOT NULL DEFAULT 0,
            automation_fit REAL,
            application_type TEXT,
            discovery_score REAL,
            discovery_status TEXT,
            discovery_reason TEXT,
            application_status TEXT
                NOT NULL DEFAULT 'not_started',
            human_approval_required INTEGER
                NOT NULL DEFAULT 1,
            published_at TEXT,
            first_seen_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS
        idx_paid_work_status
        ON paid_work_opportunities(
            discovery_status,
            discovery_score DESC
        );

        CREATE INDEX IF NOT EXISTS
        idx_paid_work_source
        ON paid_work_opportunities(
            source,
            last_seen_at DESC
        );

        CREATE INDEX IF NOT EXISTS
        idx_paid_work_payment
        ON paid_work_opportunities(
            explicit_payment,
            currency,
            maximum_amount DESC
        );
        """
    )

    conn.commit()


def save_candidate(
    conn: sqlite3.Connection,
    item: dict[str, Any],
) -> None:
    key = stable_key(
        item["source"],
        item["external_id"],
        item["url"],
        item["title"],
    )

    now = utc_now()

    conn.execute(
        """
        INSERT INTO paid_work_opportunities (
            candidate_key,
            source,
            external_id,
            title,
            organization,
            description,
            url,
            location,
            remote,
            tags,
            employment_type,
            salary,
            minimum_amount,
            maximum_amount,
            currency,
            payment_evidence,
            explicit_payment,
            remote_confirmed,
            automation_fit,
            application_type,
            discovery_score,
            discovery_status,
            discovery_reason,
            application_status,
            human_approval_required,
            published_at,
            first_seen_at,
            last_seen_at
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, 'not_started', 1, ?, ?, ?
        )
        ON CONFLICT(candidate_key) DO UPDATE SET
            title = excluded.title,
            organization = excluded.organization,
            description = excluded.description,
            url = excluded.url,
            location = excluded.location,
            remote = excluded.remote,
            tags = excluded.tags,
            employment_type =
                excluded.employment_type,
            salary = excluded.salary,
            minimum_amount =
                excluded.minimum_amount,
            maximum_amount =
                excluded.maximum_amount,
            currency = excluded.currency,
            payment_evidence =
                excluded.payment_evidence,
            explicit_payment =
                excluded.explicit_payment,
            remote_confirmed =
                excluded.remote_confirmed,
            automation_fit =
                excluded.automation_fit,
            application_type =
                excluded.application_type,
            discovery_score =
                excluded.discovery_score,
            discovery_status =
                excluded.discovery_status,
            discovery_reason =
                excluded.discovery_reason,
            published_at =
                excluded.published_at,
            last_seen_at =
                excluded.last_seen_at
        """,
        (
            key,
            item["source"],
            item["external_id"],
            item["title"],
            item["organization"],
            item["description"],
            item["url"],
            item["location"],
            item["remote"],
            item["tags"],
            item["employment_type"],
            item["salary"],
            item["minimum_amount"],
            item["maximum_amount"],
            item["currency"],
            item["payment_evidence"],
            item["explicit_payment"],
            item["remote_confirmed"],
            item["automation_fit"],
            item["application_type"],
            item["discovery_score"],
            item["discovery_status"],
            item["discovery_reason"],
            item["published_at"],
            now,
            now,
        ),
    )


collectors = (
    (
        "Arbeitnow",
        fetch_arbeitnow,
    ),
    (
        "Remotive",
        fetch_remotive,
    ),
    (
        "Remote OK",
        fetch_remoteok,
    ),
    (
        "GitHub paid issues",
        fetch_github_paid_issues,
    ),
)


connection = sqlite3.connect(
    DATABASE
)

connection.row_factory = sqlite3.Row
ensure_schema(connection)

all_candidates = []
source_counts = {}
errors = []

print()
print("===== GLOBAL PAID WORK DISCOVERY =====")

for name, collector in collectors:
    try:
        rows = collector()
        source_counts[name] = len(rows)

        print(
            f"{name}: {len(rows)} received"
        )

        for raw in rows:
            if (
                not raw.get("title")
                or not raw.get("url")
            ):
                continue

            classified = classify(raw)
            save_candidate(
                connection,
                classified,
            )

            all_candidates.append(
                classified
            )

        connection.commit()

    except Exception as error:
        connection.rollback()
        log_error(name, error)

        errors.append(
            f"{name}: "
            f"{type(error).__name__}: "
            f"{error}"
        )

        print(
            f"{name}: ERROR — "
            f"{type(error).__name__}: "
            f"{error}"
        )


ranked = connection.execute(
    """
    SELECT
        source,
        title,
        organization,
        url,
        location,
        employment_type,
        salary,
        minimum_amount,
        maximum_amount,
        currency,
        payment_evidence,
        explicit_payment,
        remote_confirmed,
        automation_fit,
        application_type,
        discovery_score,
        discovery_status,
        discovery_reason,
        published_at
    FROM paid_work_opportunities
    WHERE discovery_status IN (
        'actionable_review',
        'manual_review'
    )
    ORDER BY
        CASE discovery_status
            WHEN 'actionable_review'
            THEN 1
            ELSE 2
        END,
        discovery_score DESC,
        COALESCE(
            maximum_amount,
            minimum_amount,
            0
        ) DESC
    LIMIT 200
    """
).fetchall()


counts = {
    row["discovery_status"]: row["total"]
    for row in connection.execute(
        """
        SELECT
            discovery_status,
            COUNT(*) AS total
        FROM paid_work_opportunities
        GROUP BY discovery_status
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
    "location",
    "employment_type",
    "salary",
    "minimum_amount",
    "maximum_amount",
    "currency",
    "payment_evidence",
    "explicit_payment",
    "remote_confirmed",
    "automation_fit",
    "application_type",
    "discovery_score",
    "discovery_status",
    "discovery_reason",
    "published_at",
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
        writer.writerow(dict(row))


lines = [
    "# Global Revenue Brain — Paid Work Discovery",
    "",
    f"Gerado em: {utc_now()}",
    "",
    "## Objetivo",
    "",
    "Encontrar globalmente tarefas, contratos e serviços "
    "remotos com intenção explícita de pagamento e "
    "compatibilidade com execução digital.",
    "",
    "Nenhuma candidatura, proposta, aceite contratual "
    "ou ação externa foi realizada.",
    "",
    "## Resumo",
    "",
    f"- Total coletado nesta execução: "
    f"**{len(all_candidates)}**",
    f"- Actionable review: "
    f"**{counts.get('actionable_review', 0)}**",
    f"- Manual review: "
    f"**{counts.get('manual_review', 0)}**",
    f"- Low priority: "
    f"**{counts.get('low_priority', 0)}**",
    f"- Rejected: "
    f"**{counts.get('rejected', 0)}**",
    f"- Erros: **{len(errors)}**",
    "",
    "## Fontes",
    "",
]


for source, total in source_counts.items():
    lines.append(
        f"- {source}: **{total}**"
    )


if errors:
    lines.extend([
        "",
        "## Erros",
        "",
    ])

    for error in errors:
        lines.append(
            f"- {error}"
        )


lines.extend([
    "",
    "## Melhores oportunidades",
    "",
])


for index, row in enumerate(
    ranked[:50],
    1,
):
    if (
        row["minimum_amount"]
        is not None
    ):
        if (
            row["maximum_amount"]
            != row["minimum_amount"]
        ):
            reward = (
                f"{row['currency']} "
                f"{row['minimum_amount']:,.2f}"
                f"–{row['maximum_amount']:,.2f}"
            )
        else:
            reward = (
                f"{row['currency']} "
                f"{row['minimum_amount']:,.2f}"
            )
    elif row["salary"]:
        reward = row["salary"]
    else:
        reward = "não confirmado"

    lines.extend([
        f"### {index}. {row['title']}",
        "",
        f"- Fonte: {row['source']}",
        f"- Contratante: "
        f"{row['organization']}",
        f"- Localização: "
        f"{row['location']}",
        f"- Tipo: "
        f"{row['employment_type']}",
        f"- Remuneração: {reward}",
        f"- Evidência de pagamento: "
        f"{row['payment_evidence'] or 'não encontrada'}",
        f"- Execução remota: "
        f"{'sim' if row['remote_confirmed'] else 'não confirmada'}",
        f"- Compatibilidade com automação: "
        f"{row['automation_fit'] * 100:.1f}%",
        f"- Score: "
        f"**{row['discovery_score']}**",
        f"- Status: "
        f"**{row['discovery_status']}**",
        f"- Forma de entrada: "
        f"{row['application_type']}",
        f"- Motivo: "
        f"{row['discovery_reason']}",
        f"- URL: {row['url']}",
        "",
    ])


REPORT_PATH.write_text(
    "\n".join(lines),
    encoding="utf-8",
)


print()
print("===== PAID WORK SUMMARY =====")
print(
    "Collected:",
    len(all_candidates),
)
print(
    "Actionable review:",
    counts.get(
        "actionable_review",
        0,
    ),
)
print(
    "Manual review:",
    counts.get(
        "manual_review",
        0,
    ),
)
print(
    "Low priority:",
    counts.get(
        "low_priority",
        0,
    ),
)
print(
    "Rejected:",
    counts.get(
        "rejected",
        0,
    ),
)
print(
    "Errors:",
    len(errors),
)


print()
print("===== TOP 20 PAID WORK =====")

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
        f"   organization: "
        f"{row['organization']}"
    )
    print(
        f"   status: "
        f"{row['discovery_status']}"
    )
    print(
        f"   score: "
        f"{row['discovery_score']}"
    )
    print(
        f"   automation fit: "
        f"{row['automation_fit'] * 100:.1f}%"
    )
    print(
        f"   salary/evidence: "
        f"{row['salary'] or row['payment_evidence'] or 'not confirmed'}"
    )
    print(
        f"   location: "
        f"{row['location']}"
    )
    print(
        f"   url: {row['url']}"
    )


connection.close()
