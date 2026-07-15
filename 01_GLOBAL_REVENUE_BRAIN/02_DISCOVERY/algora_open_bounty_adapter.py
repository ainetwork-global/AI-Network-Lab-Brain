from __future__ import annotations

import csv
import hashlib
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "11_DATA" / "global_revenue_brain.db"
REPORT = ROOT / "12_REPORTS" / "LATEST_ALGORA_OPEN_BOUNTIES.md"
CSV_PATH = ROOT / "04_OPPORTUNITIES" / "algora_open_bounties.csv"

COMMUNITY_URL = "https://algora.io/community"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; GlobalRevenueBrain/1.3; "
        "+https://github.com/ainetwork-global/AI-Network-Lab-Brain)"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}

RESERVED_PATHS = {
    "",
    "community",
    "auth",
    "login",
    "signup",
    "about",
    "pricing",
    "docs",
    "blog",
    "bounties",
    "jobs",
    "terms",
    "privacy",
}

NEGATIVE_TITLE_TERMS = (
    "completed",
    "closed",
    "awarded to",
    "leaderboard",
    "no open bounties",
)

SKILL_TERMS = {
    "python": "Python",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "react": "React",
    "next.js": "Next.js",
    "node": "Node.js",
    "rust": "Rust",
    "golang": "Go",
    " go ": "Go",
    "java": "Java",
    "documentation": "Documentação",
    "docs": "Documentação",
    "api": "API",
    "sql": "SQL",
    "postgres": "PostgreSQL",
    "docker": "Docker",
    "test": "Testes",
}

MONEY_PATTERNS = [
    re.compile(
        r"(?:US\$|USD|\$)\s*(\d[\d,.]*(?:\.\d{1,2})?)",
        re.I,
    ),
    re.compile(
        r"(\d[\d,.]*(?:\.\d{1,2})?)\s*(?:USD|USDC)",
        re.I,
    ),
]

GITHUB_ISSUE_PATTERN = re.compile(
    r"https://github\.com/([^/]+)/([^/]+)/(?:issues|pull)/(\d+)",
    re.I,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def parse_amount(text: str) -> float | None:
    for pattern in MONEY_PATTERNS:
        match = pattern.search(text)

        if not match:
            continue

        raw = match.group(1).replace(",", "")

        try:
            amount = float(raw)

            if amount > 0:
                return amount
        except ValueError:
            continue

    return None


def candidate_key(url: str) -> str:
    return hashlib.sha256(
        f"Algora|{url}".encode("utf-8")
    ).hexdigest()


def extract_skills(text: str) -> list[str]:
    lowered = f" {text.lower()} "

    skills = {
        label
        for term, label in SKILL_TERMS.items()
        if term in lowered
    }

    return sorted(skills)


def initialize_database(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS algora_open_bounties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_key TEXT NOT NULL UNIQUE,
            organization TEXT NOT NULL,
            title TEXT NOT NULL,
            algora_url TEXT NOT NULL,
            github_url TEXT,
            github_owner TEXT,
            github_repository TEXT,
            github_issue_number INTEGER,
            reward_amount REAL NOT NULL,
            reward_currency TEXT NOT NULL DEFAULT 'USD',
            skills TEXT,
            claim_count INTEGER,
            open_status INTEGER NOT NULL DEFAULT 1,
            candidate_score REAL NOT NULL,
            verification_status TEXT NOT NULL DEFAULT 'staged',
            discovered_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_algora_open_score
        ON algora_open_bounties(candidate_score DESC);

        CREATE INDEX IF NOT EXISTS idx_algora_open_status
        ON algora_open_bounties(open_status, verification_status);
        """
    )

    connection.commit()


def fetch_soup(url: str) -> tuple[requests.Response, BeautifulSoup]:
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30,
        allow_redirects=True,
    )
    response.raise_for_status()

    return response, BeautifulSoup(response.text, "html.parser")


def discover_organizations() -> list[str]:
    organizations = {
        "tscircuit",
        "Dokploy",
        "CapSoftware",
        "arakoodev",
        "mediar-ai",
        "databuddy-analytics",
        "PrimeIntellect-ai",
        "activepieces",
        "comet-ml",
        "highlight",
        "coollabsio",
        "archestra-ai",
        "algora",
        "mendableai",
    }

    try:
        response, soup = fetch_soup("https://algora.io/")

        for anchor in soup.find_all("a", href=True):
            absolute = urldefrag(
                urljoin(response.url, anchor["href"])
            )[0]

            parsed = urlparse(absolute)

            if parsed.hostname not in {"algora.io", "www.algora.io"}:
                continue

            match = re.match(
                r"^/([A-Za-z0-9_.-]+)/bounties",
                parsed.path,
                re.IGNORECASE,
            )

            if not match:
                continue

            organization = match.group(1)

            if organization.lower() not in RESERVED_PATHS:
                organizations.add(organization)

    except Exception as error:
        print(
            "Aviso: descoberta complementar na página inicial falhou: "
            f"{error}"
        )

    return sorted(organizations)


def extract_bounties_from_page(
    organization: str,
    page_url: str,
) -> list[dict]:
    response, soup = fetch_soup(page_url)
    results: dict[str, dict] = {}

    page_text = clean(soup.get_text(" ", strip=True))

    if "no open bounties" in page_text.lower():
        return []

    for anchor in soup.find_all("a", href=True):
        title = clean(anchor.get_text(" ", strip=True))

        if not title or len(title) < 8:
            continue

        if any(
            term in title.lower()
            for term in NEGATIVE_TITLE_TERMS
        ):
            continue

        absolute = urldefrag(
            urljoin(response.url, anchor["href"])
        )[0]

        parent = anchor

        for _ in range(4):
            if parent.parent:
                parent = parent.parent

        context = clean(
            parent.get_text(" ", strip=True)
            if parent
            else title
        )[:2000]

        combined = f"{title} {context}"

        amount = parse_amount(combined)

        if amount is None:
            continue

        github_match = GITHUB_ISSUE_PATTERN.search(
            f"{absolute} {context}"
        )

        github_url = None
        github_owner = None
        github_repository = None
        github_issue_number = None

        if github_match:
            github_owner = github_match.group(1)
            github_repository = github_match.group(2)
            github_issue_number = int(github_match.group(3))
            github_url = github_match.group(0)

        claim_match = re.search(
            r"(\d+)\s+claims?",
            combined,
            re.I,
        )

        claim_count = (
            int(claim_match.group(1))
            if claim_match
            else None
        )

        skills = extract_skills(combined)

        score = 55.0

        if github_url:
            score += 15

        if amount >= 1_000:
            score += 15
        elif amount >= 500:
            score += 12
        elif amount >= 100:
            score += 8
        elif amount < 25:
            score -= 12

        if skills:
            score += min(10, len(skills) * 2)

        if claim_count is not None:
            if claim_count == 0:
                score += 8
            elif claim_count <= 3:
                score += 3
            elif claim_count >= 10:
                score -= 15

        if "open" in combined.lower():
            score += 5

        item_url = github_url or absolute
        key = candidate_key(item_url)

        results[key] = {
            "candidate_key": key,
            "organization": organization,
            "title": title,
            "algora_url": absolute,
            "github_url": github_url,
            "github_owner": github_owner,
            "github_repository": github_repository,
            "github_issue_number": github_issue_number,
            "reward_amount": amount,
            "reward_currency": "USD",
            "skills": ", ".join(skills),
            "claim_count": claim_count,
            "candidate_score": round(
                max(0, min(100, score)),
                2,
            ),
        }

    return list(results.values())


def save_bounty(
    connection: sqlite3.Connection,
    item: dict,
) -> None:
    connection.execute(
        """
        INSERT INTO algora_open_bounties (
            candidate_key,
            organization,
            title,
            algora_url,
            github_url,
            github_owner,
            github_repository,
            github_issue_number,
            reward_amount,
            reward_currency,
            skills,
            claim_count,
            open_status,
            candidate_score,
            verification_status,
            discovered_at,
            last_seen_at
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, 1, ?, 'staged', ?, ?
        )
        ON CONFLICT(candidate_key) DO UPDATE SET
            organization = excluded.organization,
            title = excluded.title,
            algora_url = excluded.algora_url,
            github_url = excluded.github_url,
            github_owner = excluded.github_owner,
            github_repository = excluded.github_repository,
            github_issue_number = excluded.github_issue_number,
            reward_amount = excluded.reward_amount,
            reward_currency = excluded.reward_currency,
            skills = excluded.skills,
            claim_count = excluded.claim_count,
            open_status = 1,
            candidate_score = excluded.candidate_score,
            last_seen_at = excluded.last_seen_at
        """,
        (
            item["candidate_key"],
            item["organization"],
            item["title"],
            item["algora_url"],
            item["github_url"],
            item["github_owner"],
            item["github_repository"],
            item["github_issue_number"],
            item["reward_amount"],
            item["reward_currency"],
            item["skills"],
            item["claim_count"],
            item["candidate_score"],
            utc_now(),
            utc_now(),
        ),
    )


connection = sqlite3.connect(DATABASE)
connection.row_factory = sqlite3.Row
initialize_database(connection)

print()
print("===== ALGORA OPEN BOUNTY ADAPTER =====")

organizations = discover_organizations()

print(f"Organizações descobertas: {len(organizations)}")

all_items: dict[str, dict] = {}
healthy_pages = 0
errors = []

for index, organization in enumerate(
    organizations,
    start=1,
):
    page_url = (
        f"https://algora.io/{organization}"
        f"/bounties?status=open"
    )

    try:
        items = extract_bounties_from_page(
            organization,
            page_url,
        )

        healthy_pages += 1

        for item in items:
            all_items[item["candidate_key"]] = item

        if items:
            print()
            print(
                f"[{index}/{len(organizations)}] "
                f"{organization}: {len(items)}"
            )

        time.sleep(0.15)

    except Exception as error:
        errors.append(
            f"{organization}: {error}"
        )

for item in all_items.values():
    save_bounty(connection, item)

connection.commit()

rows = connection.execute(
    """
    SELECT *
    FROM algora_open_bounties
    WHERE open_status = 1
      AND verification_status = 'staged'
    ORDER BY
        candidate_score DESC,
        reward_amount DESC,
        COALESCE(claim_count, 999999),
        title
    """
).fetchall()

CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT.parent.mkdir(parents=True, exist_ok=True)

fields = [
    "id",
    "organization",
    "title",
    "algora_url",
    "github_url",
    "github_owner",
    "github_repository",
    "github_issue_number",
    "reward_amount",
    "reward_currency",
    "skills",
    "claim_count",
    "candidate_score",
    "verification_status",
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

    for row in rows:
        writer.writerow(
            {
                field: row[field]
                for field in fields
            }
        )

lines = [
    "# Global Revenue Brain — Algora Open Bounties",
    "",
    f"Gerado em: {utc_now()}",
    "",
    "## Resumo",
    "",
    f"- Organizações descobertas: **{len(organizations)}**",
    f"- Páginas saudáveis: **{healthy_pages}**",
    f"- Bounties abertas identificadas: **{len(rows)}**",
    f"- Erros: **{len(errors)}**",
    "",
    "## Ranking",
    "",
]

for index, row in enumerate(rows, start=1):
    lines.extend(
        [
            f"### {index}. {row['title']}",
            "",
            f"- Organização: {row['organization']}",
            f"- Recompensa: **USD {row['reward_amount']:,.2f}**",
            f"- Score: **{row['candidate_score']}**",
            f"- Claims: {row['claim_count'] if row['claim_count'] is not None else 'não identificado'}",
            f"- Competências: {row['skills'] or 'não identificadas'}",
            f"- GitHub: {row['github_url'] or 'não identificado'}",
            f"- Algora: {row['algora_url']}",
            "",
        ]
    )

if errors:
    lines.extend(
        [
            "## Erros",
            "",
        ]
    )

    for error in errors[:30]:
        lines.append(f"- {error}")

REPORT.write_text(
    "\n".join(lines),
    encoding="utf-8",
)

print()
print("===== ALGORA SUMMARY =====")
print(f"Organizações descobertas: {len(organizations)}")
print(f"Páginas saudáveis: {healthy_pages}")
print(f"Bounties abertas: {len(rows)}")
print(f"Erros: {len(errors)}")

print()
print("===== TOP 20 ALGORA OPEN BOUNTIES =====")

for index, row in enumerate(
    rows[:20],
    start=1,
):
    print()
    print(f"{index}. {row['title']}")
    print(f"   organização: {row['organization']}")
    print(f"   recompensa: USD {row['reward_amount']}")
    print(f"   score: {row['candidate_score']}")
    print(
        f"   claims: "
        f"{row['claim_count'] if row['claim_count'] is not None else 'não identificado'}"
    )
    print(
        f"   competências: "
        f"{row['skills'] or 'não identificadas'}"
    )
    print(
        f"   github: "
        f"{row['github_url'] or 'não identificado'}"
    )
    print(f"   algora: {row['algora_url']}")

connection.close()
