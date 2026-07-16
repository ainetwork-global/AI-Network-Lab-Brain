from __future__ import annotations

import csv
import hashlib
import html
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "11_DATA" / "global_revenue_brain.db"
REPORT = ROOT / "12_REPORTS" / "LATEST_DEVPOST_HACKATHONS.md"
CSV_PATH = ROOT / "04_OPPORTUNITIES" / "devpost_hackathons.csv"

API_URL = "https://devpost.com/api/hackathons"
LISTING_URL = "https://devpost.com/hackathons"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; GlobalRevenueBrain/1.4; "
        "+https://github.com/ainetwork-global/AI-Network-Lab-Brain)"
    ),
    "Accept": "application/json,text/html,application/xhtml+xml,*/*;q=0.8",
}

MONEY_PATTERNS = [
    re.compile(
        r"(?:US\$|USD|\$)\s*"
        r"(?P<amount>\d[\d,.]*(?:\.\d{1,2})?)"
        r"(?:\s*(?P<suffix>[kKmM]))?",
        re.I,
    ),
    re.compile(
        r"(?P<amount>\d[\d,.]*(?:\.\d{1,2})?)"
        r"(?:\s*(?P<suffix>[kKmM]))?\s*"
        r"(?:USD|US dollars?|in cash|in prizes?)",
        re.I,
    ),
]

NEGATIVE_TERMS = (
    "ended",
    "closed",
    "winners announced",
    "submissions closed",
    "past hackathon",
)

AI_TERMS = (
    "artificial intelligence",
    " ai ",
    "machine learning",
    "llm",
    "agent",
    "automation",
    "api",
    "cloud",
    "developer",
    "open source",
    "cybersecurity",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean(value: object) -> str:
    return re.sub(
        r"\s+",
        " ",
        html.unescape(str(value or "")),
    ).strip()


def candidate_key(url: str) -> str:
    return hashlib.sha256(
        f"Devpost|{url}".encode("utf-8")
    ).hexdigest()


def parse_amount(text: str) -> float | None:
    for pattern in MONEY_PATTERNS:
        match = pattern.search(text)

        if not match:
            continue

        raw = match.group("amount").replace(",", "")
        suffix = (match.groupdict().get("suffix") or "").lower()

        try:
            amount = float(raw)
        except ValueError:
            continue

        if suffix == "k":
            amount *= 1_000
        elif suffix == "m":
            amount *= 1_000_000

        if amount > 0:
            return amount

    return None


def parse_date(value: object) -> str | None:
    text = clean(value)

    if not text:
        return None

    try:
        return date_parser.parse(text, fuzzy=True).date().isoformat()
    except (ValueError, TypeError, OverflowError):
        return None


def initialize_database(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS devpost_hackathons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_key TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            organization TEXT,
            description TEXT,
            reward_amount REAL,
            reward_currency TEXT DEFAULT 'USD',
            start_date TEXT,
            end_date TEXT,
            location TEXT,
            online INTEGER,
            participants INTEGER,
            status TEXT,
            skills TEXT,
            candidate_score REAL NOT NULL,
            verification_status TEXT NOT NULL DEFAULT 'staged',
            discovered_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_devpost_score
        ON devpost_hackathons(candidate_score DESC);

        CREATE INDEX IF NOT EXISTS idx_devpost_status
        ON devpost_hackathons(status, verification_status);
        """
    )

    connection.commit()


def normalize_api_item(item: dict) -> dict | None:
    title = clean(
        item.get("title")
        or item.get("name")
        or item.get("hackathon_name")
    )

    url = clean(
        item.get("url")
        or item.get("submission_url")
        or item.get("hackathon_url")
    )

    if url and url.startswith("/"):
        url = urljoin("https://devpost.com", url)

    if not title or not url:
        return None

    description = clean(
        item.get("description")
        or item.get("tagline")
        or item.get("excerpt")
    )

    organization = clean(
        item.get("organization_name")
        or item.get("organization")
        or item.get("host")
    )

    prize_text = clean(
        item.get("prize_amount")
        or item.get("prize")
        or item.get("prizes")
        or item.get("prize_description")
    )

    combined = f"{title} {description} {prize_text}"
    reward_amount = parse_amount(combined)

    start_date = parse_date(
        item.get("start_date")
        or item.get("starts_at")
        or item.get("submission_period_dates")
    )

    end_date = parse_date(
        item.get("end_date")
        or item.get("ends_at")
        or item.get("submission_deadline")
    )

    status = clean(item.get("status")).lower() or "unknown"

    return {
        "title": title,
        "url": url,
        "organization": organization,
        "description": description,
        "reward_amount": reward_amount,
        "start_date": start_date,
        "end_date": end_date,
        "location": clean(item.get("location")),
        "online": int(bool(item.get("online") or item.get("is_online"))),
        "participants": item.get("registrations_count")
        or item.get("participants_count"),
        "status": status,
    }


def fetch_from_api() -> list[dict]:
    results: dict[str, dict] = {}

    for page in range(1, 11):
        response = requests.get(
            API_URL,
            params=[
                ("status[]", "open"),
                ("status[]", "upcoming"),
                ("page", page),
            ],
            headers=HEADERS,
            timeout=30,
        )

        if response.status_code != 200:
            if page == 1:
                raise RuntimeError(
                    f"API Devpost retornou HTTP {response.status_code}"
                )
            break

        data = response.json()

        items = (
            data.get("hackathons")
            or data.get("results")
            or data.get("items")
            or []
        )

        if not items:
            break

        for raw_item in items:
            if not isinstance(raw_item, dict):
                continue

            item = normalize_api_item(raw_item)

            if item:
                results[item["url"]] = item

        if len(items) < 10:
            break

    return list(results.values())


def extract_json_objects(soup: BeautifulSoup) -> list[dict]:
    found: list[dict] = []

    for script in soup.find_all("script"):
        script_type = clean(script.get("type")).lower()
        content = script.string or script.get_text() or ""

        if not content.strip():
            continue

        if script_type in {
            "application/ld+json",
            "application/json",
        }:
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                continue

            stack = [parsed]

            while stack:
                value = stack.pop()

                if isinstance(value, dict):
                    found.append(value)
                    stack.extend(value.values())
                elif isinstance(value, list):
                    stack.extend(value)

    return found


def fetch_from_html() -> list[dict]:
    response = requests.get(
        LISTING_URL,
        params=[
            ("status[]", "open"),
            ("status[]", "upcoming"),
        ],
        headers=HEADERS,
        timeout=30,
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    results: dict[str, dict] = {}

    for raw_item in extract_json_objects(soup):
        item = normalize_api_item(raw_item)

        if item:
            results[item["url"]] = item

    for anchor in soup.find_all("a", href=True):
        absolute_url = urljoin(response.url, anchor["href"])
        hostname = (urlparse(absolute_url).hostname or "").lower()

        if not (
            hostname == "devpost.com"
            or hostname.endswith(".devpost.com")
        ):
            continue

        title = clean(anchor.get_text(" ", strip=True))

        if len(title) < 8:
            continue

        parent = anchor

        for _ in range(4):
            if parent.parent:
                parent = parent.parent

        context = clean(
            parent.get_text(" ", strip=True)
            if parent
            else title
        )[:3000]

        lowered = context.lower()

        if any(term in lowered for term in NEGATIVE_TERMS):
            continue

        reward_amount = parse_amount(context)

        if reward_amount is None:
            continue

        results[absolute_url] = {
            "title": title,
            "url": absolute_url,
            "organization": "",
            "description": context,
            "reward_amount": reward_amount,
            "start_date": None,
            "end_date": None,
            "location": "",
            "online": int("online" in lowered),
            "participants": None,
            "status": "open_or_upcoming",
        }

    return list(results.values())


def score_candidate(item: dict) -> tuple[float, str]:
    combined = clean(
        f"{item['title']} {item['description']}"
    ).lower()

    score = 50.0
    matched_skills = []

    if item["reward_amount"]:
        score += 15

        if item["reward_amount"] >= 100_000:
            score += 12
        elif item["reward_amount"] >= 10_000:
            score += 10
        elif item["reward_amount"] >= 1_000:
            score += 7

    if item["end_date"]:
        score += 8

        try:
            deadline = date_parser.parse(item["end_date"]).date()
            days = (
                deadline - datetime.now(timezone.utc).date()
            ).days

            if days < 0:
                score = 0
            elif days < 7:
                score -= 15
            elif days >= 21:
                score += 5
        except (ValueError, TypeError):
            pass

    for term in AI_TERMS:
        if term in f" {combined} ":
            matched_skills.append(term.strip())

    if matched_skills:
        score += min(12, len(matched_skills) * 3)

    if item["online"]:
        score += 5

    return (
        round(max(0, min(100, score)), 2),
        ", ".join(sorted(set(matched_skills))),
    )


def save_candidate(
    connection: sqlite3.Connection,
    item: dict,
) -> None:
    score, skills = score_candidate(item)

    if score < 45:
        return

    connection.execute(
        """
        INSERT INTO devpost_hackathons (
            candidate_key,
            title,
            url,
            organization,
            description,
            reward_amount,
            reward_currency,
            start_date,
            end_date,
            location,
            online,
            participants,
            status,
            skills,
            candidate_score,
            verification_status,
            discovered_at,
            last_seen_at
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, 'USD', ?, ?, ?, ?,
            ?, ?, ?, ?, 'staged', ?, ?
        )
        ON CONFLICT(candidate_key) DO UPDATE SET
            title = excluded.title,
            organization = excluded.organization,
            description = excluded.description,
            reward_amount = excluded.reward_amount,
            start_date = excluded.start_date,
            end_date = excluded.end_date,
            location = excluded.location,
            online = excluded.online,
            participants = excluded.participants,
            status = excluded.status,
            skills = excluded.skills,
            candidate_score = excluded.candidate_score,
            last_seen_at = excluded.last_seen_at
        """,
        (
            candidate_key(item["url"]),
            item["title"],
            item["url"],
            item["organization"],
            item["description"],
            item["reward_amount"],
            item["start_date"],
            item["end_date"],
            item["location"],
            item["online"],
            item["participants"],
            item["status"],
            skills,
            score,
            utc_now(),
            utc_now(),
        ),
    )


connection = sqlite3.connect(DATABASE)
connection.row_factory = sqlite3.Row
initialize_database(connection)

print()
print("===== DEVPOST OFFICIAL ADAPTER =====")

method = None
errors = []

try:
    items = fetch_from_api()
    method = "api"
except Exception as error:
    errors.append(f"API: {error}")
    items = []

if not items:
    try:
        items = fetch_from_html()
        method = "html"
    except Exception as error:
        errors.append(f"HTML: {error}")
        items = []

for item in items:
    save_candidate(connection, item)

connection.commit()

rows = connection.execute(
    """
    SELECT *
    FROM devpost_hackathons
    WHERE verification_status = 'staged'
    ORDER BY
        candidate_score DESC,
        reward_amount DESC,
        COALESCE(end_date, '9999-12-31'),
        title
    """
).fetchall()

CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT.parent.mkdir(parents=True, exist_ok=True)

fields = [
    "id",
    "title",
    "url",
    "organization",
    "reward_amount",
    "reward_currency",
    "start_date",
    "end_date",
    "location",
    "online",
    "participants",
    "status",
    "skills",
    "candidate_score",
    "verification_status",
]

with CSV_PATH.open(
    "w",
    encoding="utf-8-sig",
    newline="",
) as file:
    writer = csv.DictWriter(file, fieldnames=fields)
    writer.writeheader()

    for row in rows:
        writer.writerow({
            field: row[field]
            for field in fields
        })

lines = [
    "# Global Revenue Brain — Devpost Hackathons",
    "",
    f"Gerado em: {utc_now()}",
    "",
    "## Resumo",
    "",
    f"- Método utilizado: **{method or 'nenhum'}**",
    f"- Registros recebidos: **{len(items)}**",
    f"- Candidatos staged: **{len(rows)}**",
    f"- Erros: **{len(errors)}**",
    "",
    "## Ranking",
    "",
]

for index, row in enumerate(rows, start=1):
    reward = (
        f"USD {row['reward_amount']:,.2f}"
        if row["reward_amount"] is not None
        else "não identificada"
    )

    lines.extend([
        f"### {index}. {row['title']}",
        "",
        f"- Organização: {row['organization'] or 'não identificada'}",
        f"- Recompensa: **{reward}**",
        f"- Score: **{row['candidate_score']}**",
        f"- Início: {row['start_date'] or 'não identificado'}",
        f"- Prazo: {row['end_date'] or 'não identificado'}",
        f"- Online: {'sim' if row['online'] else 'não identificado'}",
        f"- Participantes: {row['participants'] or 'não identificado'}",
        f"- Competências: {row['skills'] or 'não identificadas'}",
        f"- URL: {row['url']}",
        "",
    ])

if errors:
    lines.extend(["## Erros", ""])

    for error in errors:
        lines.append(f"- {error}")

REPORT.write_text("\n".join(lines), encoding="utf-8")

print(f"Método: {method or 'nenhum'}")
print(f"Registros recebidos: {len(items)}")
print(f"Candidatos staged: {len(rows)}")
print(f"Erros: {len(errors)}")

print()
print("===== TOP 20 DEVPOST HACKATHONS =====")

for index, row in enumerate(rows[:20], start=1):
    reward = (
        f"USD {row['reward_amount']}"
        if row["reward_amount"] is not None
        else "não identificada"
    )

    print()
    print(f"{index}. {row['title']}")
    print(f"   organização: {row['organization'] or 'não identificada'}")
    print(f"   recompensa: {reward}")
    print(f"   score: {row['candidate_score']}")
    print(f"   prazo: {row['end_date']}")
    print(f"   online: {row['online']}")
    print(f"   skills: {row['skills'] or 'não identificadas'}")
    print(f"   url: {row['url']}")

connection.close()
