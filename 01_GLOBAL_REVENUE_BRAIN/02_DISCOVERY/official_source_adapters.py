from __future__ import annotations

import csv
import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag

import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "11_DATA" / "global_revenue_brain.db"
REPORT = ROOT / "12_REPORTS" / "LATEST_OFFICIAL_SOURCE_ADAPTERS.md"
CSV_PATH = ROOT / "04_OPPORTUNITIES" / "official_source_candidates.csv"

GRANTS_API = "https://api.grants.gov/v1/api/search2"
IMMUNEFI_LISTING = "https://immunefi.com/bug-bounty/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; GlobalRevenueBrain/1.1; "
        "+https://github.com/ainetwork-global/AI-Network-Lab-Brain)"
    ),
    "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
}

GRANT_KEYWORDS = [
    "artificial intelligence",
    "machine learning",
    "software development",
    "cybersecurity",
    "open source",
    "small business innovation",
]

NAVIGATION_TITLES = {
    "contests",
    "leaderboards",
    "bug bounties",
    "featured",
    "projects",
    "about",
    "home",
    "learn",
    "resources",
}

MONEY_PATTERNS = [
    re.compile(
        r"(?:maximum bounty|bounty|reward|award ceiling|estimated total funding)"
        r"[^$\d]{0,80}"
        r"(?P<currency>US\$|USD|\$|EUR|€|GBP|£)\s*"
        r"(?P<amount>\d[\d,.]*(?:\s*[kKmM])?)",
        re.I,
    ),
    re.compile(
        r"(?P<currency>US\$|USD|\$|EUR|€|GBP|£)\s*"
        r"(?P<amount>\d[\d,.]*(?:\s*[kKmM])?)"
        r"[^.\n]{0,80}"
        r"(?:maximum bounty|bounty|reward|award)",
        re.I,
    ),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def make_key(source: str, external_id: str) -> str:
    return hashlib.sha256(
        f"{source}|{external_id}".encode("utf-8")
    ).hexdigest()


def parse_amount(raw: str | None) -> float | None:
    if not raw:
        return None

    value = clean(raw).replace(" ", "")
    multiplier = 1.0

    if value.lower().endswith("k"):
        multiplier = 1_000.0
        value = value[:-1]
    elif value.lower().endswith("m"):
        multiplier = 1_000_000.0
        value = value[:-1]

    value = re.sub(r"[^\d,.-]", "", value)

    if "," in value and "." in value:
        if value.rfind(",") > value.rfind("."):
            value = value.replace(".", "").replace(",", ".")
        else:
            value = value.replace(",", "")
    elif "," in value:
        parts = value.split(",")

        if len(parts[-1]) in {1, 2}:
            value = value.replace(".", "").replace(",", ".")
        else:
            value = value.replace(",", "")

    try:
        return float(value) * multiplier
    except ValueError:
        return None


def extract_reward(text: str):
    for pattern in MONEY_PATTERNS:
        match = pattern.search(text)

        if match:
            currency = match.group("currency").upper()
            currency = {
                "$": "USD",
                "US$": "USD",
                "USD": "USD",
                "€": "EUR",
                "EUR": "EUR",
                "£": "GBP",
                "GBP": "GBP",
            }.get(currency, currency)

            return (
                parse_amount(match.group("amount")),
                currency,
                clean(match.group(0))[:300],
            )

    return None, None, None


def initialize_database(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS official_source_candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_key TEXT NOT NULL UNIQUE,
            source_name TEXT NOT NULL,
            external_id TEXT NOT NULL,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            description TEXT,
            reward_amount REAL,
            reward_currency TEXT,
            reward_evidence TEXT,
            open_date TEXT,
            close_date TEXT,
            status TEXT,
            eligibility TEXT,
            kyc_required INTEGER,
            capital_required INTEGER NOT NULL DEFAULT 0,
            official_domain INTEGER NOT NULL DEFAULT 1,
            candidate_score REAL NOT NULL,
            verification_status TEXT NOT NULL DEFAULT 'staged',
            discovered_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_official_candidates_score
        ON official_source_candidates(candidate_score DESC);

        CREATE INDEX IF NOT EXISTS idx_official_candidates_source
        ON official_source_candidates(source_name);

        CREATE INDEX IF NOT EXISTS idx_official_candidates_status
        ON official_source_candidates(verification_status);
        """
    )
    connection.commit()


def save_candidate(connection: sqlite3.Connection, item: dict) -> None:
    connection.execute(
        """
        INSERT INTO official_source_candidates (
            candidate_key,
            source_name,
            external_id,
            category,
            title,
            url,
            description,
            reward_amount,
            reward_currency,
            reward_evidence,
            open_date,
            close_date,
            status,
            eligibility,
            kyc_required,
            capital_required,
            official_domain,
            candidate_score,
            verification_status,
            discovered_at,
            last_seen_at
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, 1, ?, 'staged', ?, ?
        )
        ON CONFLICT(candidate_key) DO UPDATE SET
            title = excluded.title,
            url = excluded.url,
            description = excluded.description,
            reward_amount = excluded.reward_amount,
            reward_currency = excluded.reward_currency,
            reward_evidence = excluded.reward_evidence,
            open_date = excluded.open_date,
            close_date = excluded.close_date,
            status = excluded.status,
            eligibility = excluded.eligibility,
            kyc_required = excluded.kyc_required,
            capital_required = excluded.capital_required,
            candidate_score = excluded.candidate_score,
            last_seen_at = excluded.last_seen_at
        """,
        (
            item["candidate_key"],
            item["source_name"],
            item["external_id"],
            item["category"],
            item["title"],
            item["url"],
            item.get("description"),
            item.get("reward_amount"),
            item.get("reward_currency"),
            item.get("reward_evidence"),
            item.get("open_date"),
            item.get("close_date"),
            item.get("status"),
            item.get("eligibility"),
            item.get("kyc_required"),
            item.get("capital_required", 0),
            item["candidate_score"],
            utc_now(),
            utc_now(),
        ),
    )


def scan_grants(connection: sqlite3.Connection) -> list[dict]:
    results: dict[str, dict] = {}

    for keyword in GRANT_KEYWORDS:
        payload = {
            "rows": 50,
            "keyword": keyword,
            "oppStatuses": "posted|forecasted",
            "startRecordNum": 0,
        }

        response = requests.post(
            GRANTS_API,
            json=payload,
            headers={
                **HEADERS,
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        response.raise_for_status()

        data = response.json().get("data", {})

        for hit in data.get("oppHits", []):
            external_id = str(hit.get("id") or hit.get("number") or "").strip()
            title = clean(hit.get("title"))

            if not external_id or not title:
                continue

            status = clean(hit.get("oppStatus")).lower()
            close_date = clean(hit.get("closeDate")) or None
            open_date = clean(hit.get("openDate")) or None

            if status not in {"posted", "forecasted"}:
                continue

            score = 65.0

            if status == "posted":
                score += 10

            if close_date:
                try:
                    parsed_close = date_parser.parse(close_date).date()
                    days_remaining = (
                        parsed_close - datetime.now(timezone.utc).date()
                    ).days

                    if days_remaining < 0:
                        continue
                    elif days_remaining <= 7:
                        score -= 15
                    elif days_remaining >= 30:
                        score += 8
                except (ValueError, TypeError):
                    pass

            text = f"{title} {hit.get('agencyName', '')}".lower()

            if any(
                term in text
                for term in (
                    "artificial intelligence",
                    "machine learning",
                    "cybersecurity",
                    "software",
                    "technology",
                    "innovation",
                    "small business",
                )
            ):
                score += 10

            url = (
                "https://www.grants.gov/search-results-detail/"
                f"{external_id}"
            )

            item = {
                "candidate_key": make_key("Grants.gov API", external_id),
                "source_name": "Grants.gov API",
                "external_id": external_id,
                "category": "grant",
                "title": title,
                "url": url,
                "description": (
                    f"Agency: {clean(hit.get('agencyName'))}; "
                    f"Opportunity number: {clean(hit.get('number'))}; "
                    f"ALN: {', '.join(hit.get('alnist') or [])}"
                ),
                "reward_amount": None,
                "reward_currency": "USD",
                "reward_evidence": None,
                "open_date": open_date,
                "close_date": close_date,
                "status": status,
                "eligibility": None,
                "kyc_required": 1,
                "capital_required": 0,
                "candidate_score": min(100, score),
            }

            previous = results.get(external_id)

            if not previous or item["candidate_score"] > previous["candidate_score"]:
                results[external_id] = item

    for item in results.values():
        save_candidate(connection, item)

    connection.commit()
    return sorted(
        results.values(),
        key=lambda item: item["candidate_score"],
        reverse=True,
    )


def collect_immunefi_program_urls() -> list[str]:
    response = requests.get(
        IMMUNEFI_LISTING,
        headers=HEADERS,
        timeout=30,
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    urls: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        absolute = urldefrag(
            urljoin(response.url, anchor["href"])
        )[0]

        parsed = urlparse(absolute)
        path = parsed.path.rstrip("/")

        match = re.match(
            r"^/bug-bounty/([^/]+)(?:/(?:information|scope))?$",
            path,
            re.I,
        )

        if not match:
            continue

        slug = match.group(1).lower()

        if slug in {
            "projects",
            "featured",
            "competitions",
            "leaderboard",
        }:
            continue

        urls.add(
            f"https://immunefi.com/bug-bounty/{slug}/information/"
        )

    return sorted(urls)[:60]


def scan_immunefi(connection: sqlite3.Connection) -> list[dict]:
    results = []

    for url in collect_immunefi_program_urls():
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30,
            allow_redirects=True,
        )

        if response.status_code != 200:
            continue

        soup = BeautifulSoup(response.text, "html.parser")

        for element in soup(["script", "style", "noscript", "svg"]):
            element.decompose()

        title = clean(
            soup.find("h1").get_text(" ", strip=True)
            if soup.find("h1")
            else soup.title.get_text(" ", strip=True)
            if soup.title
            else ""
        )

        if not title or title.lower() in NAVIGATION_TITLES:
            continue

        text = clean(soup.get_text(" ", strip=True))
        reward_amount, reward_currency, reward_evidence = extract_reward(text)

        if reward_amount is None:
            continue

        slug_match = re.search(
            r"/bug-bounty/([^/]+)/",
            response.url,
            re.I,
        )

        if not slug_match:
            continue

        slug = slug_match.group(1).lower()

        kyc_required = int(
            any(
                term in text.lower()
                for term in (
                    "kyc required",
                    "know your customer",
                    "identity verification required",
                )
            )
        )

        poc_required = any(
            term in text.lower()
            for term in (
                "poc required",
                "proof of concept required",
            )
        )

        score = 75.0

        if reward_amount >= 1_000_000:
            score += 15
        elif reward_amount >= 100_000:
            score += 12
        elif reward_amount >= 10_000:
            score += 8

        if "submit a bug" in text.lower():
            score += 5

        if poc_required:
            score -= 5

        item = {
            "candidate_key": make_key("Immunefi", slug),
            "source_name": "Immunefi",
            "external_id": slug,
            "category": "authorized_bug_bounty",
            "title": title,
            "url": response.url,
            "description": text[:2000],
            "reward_amount": reward_amount,
            "reward_currency": reward_currency or "USD",
            "reward_evidence": reward_evidence,
            "open_date": None,
            "close_date": None,
            "status": "active",
            "eligibility": "Authorized program; inspect scope before testing.",
            "kyc_required": kyc_required,
            "capital_required": 0,
            "candidate_score": min(100, score),
        }

        save_candidate(connection, item)
        results.append(item)

    connection.commit()

    return sorted(
        results,
        key=lambda item: item["candidate_score"],
        reverse=True,
    )


connection = sqlite3.connect(DATABASE)
connection.row_factory = sqlite3.Row
initialize_database(connection)

print()
print("===== OFFICIAL SOURCE ADAPTERS =====")

grant_results = []
immunefi_results = []
errors = []

try:
    print()
    print("Executando Grants.gov API...")
    grant_results = scan_grants(connection)
    print(f"Grants staged: {len(grant_results)}")
except Exception as error:
    errors.append(f"Grants.gov: {error}")
    print(f"ERRO Grants.gov: {error}")

try:
    print()
    print("Executando Immunefi adapter...")
    immunefi_results = scan_immunefi(connection)
    print(f"Immunefi staged: {len(immunefi_results)}")
except Exception as error:
    errors.append(f"Immunefi: {error}")
    print(f"ERRO Immunefi: {error}")

all_rows = connection.execute(
    """
    SELECT *
    FROM official_source_candidates
    WHERE verification_status = 'staged'
    ORDER BY
        candidate_score DESC,
        reward_amount DESC,
        source_name,
        title
    LIMIT 100
    """
).fetchall()

CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT.parent.mkdir(parents=True, exist_ok=True)

fields = [
    "id",
    "source_name",
    "external_id",
    "category",
    "title",
    "url",
    "reward_amount",
    "reward_currency",
    "reward_evidence",
    "open_date",
    "close_date",
    "status",
    "eligibility",
    "kyc_required",
    "capital_required",
    "candidate_score",
    "verification_status",
]

with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=fields)
    writer.writeheader()

    for row in all_rows:
        writer.writerow({field: row[field] for field in fields})

lines = [
    "# Global Revenue Brain — Official Source Adapters",
    "",
    f"Gerado em: {utc_now()}",
    "",
    "## Resumo",
    "",
    f"- Grants.gov staged: **{len(grant_results)}**",
    f"- Immunefi staged: **{len(immunefi_results)}**",
    f"- Total isolado: **{len(all_rows)}**",
    f"- Erros: **{len(errors)}**",
    "",
]

if errors:
    lines.extend(["## Erros", ""])

    for error in errors:
        lines.append(f"- {error}")

    lines.append("")

lines.extend(["## Ranking", ""])

for index, row in enumerate(all_rows, 1):
    reward = "não identificada"

    if row["reward_amount"] is not None:
        reward = (
            f"{row['reward_currency'] or '?'} "
            f"{float(row['reward_amount']):,.2f}"
        )

    lines.extend(
        [
            f"### {index}. {row['title']}",
            "",
            f"- Fonte: {row['source_name']}",
            f"- Categoria: {row['category']}",
            f"- Score: {row['candidate_score']}",
            f"- Recompensa: {reward}",
            f"- Status: {row['status']}",
            f"- Abertura: {row['open_date'] or 'não informada'}",
            f"- Encerramento: {row['close_date'] or 'não informado'}",
            f"- KYC: {'sim' if row['kyc_required'] else 'não identificado'}",
            f"- Capital necessário: {'sim' if row['capital_required'] else 'não'}",
            f"- URL: {row['url']}",
            "",
        ]
    )

REPORT.write_text("\n".join(lines), encoding="utf-8")

print()
print("===== OFFICIAL SOURCE SUMMARY =====")
print(f"Grants.gov staged: {len(grant_results)}")
print(f"Immunefi staged: {len(immunefi_results)}")
print(f"Total isolado: {len(all_rows)}")
print(f"Erros: {len(errors)}")

print()
print("===== TOP 20 OFFICIAL CANDIDATES =====")

for index, row in enumerate(all_rows[:20], 1):
    reward = (
        f"{row['reward_currency']} {row['reward_amount']}"
        if row["reward_amount"] is not None
        else "não identificada"
    )

    print()
    print(f"{index}. {row['title']}")
    print(f"   fonte: {row['source_name']}")
    print(f"   categoria: {row['category']}")
    print(f"   recompensa: {reward}")
    print(f"   score: {row['candidate_score']}")
    print(f"   fechamento: {row['close_date']}")
    print(f"   url: {row['url']}")

connection.close()
