from __future__ import annotations

import csv
import html
import json
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "11_DATA" / "global_revenue_brain.db"
REPORT = ROOT / "12_REPORTS" / "LATEST_DEVPOST_DEEP_ENRICHMENT.md"
CSV_PATH = ROOT / "04_OPPORTUNITIES" / "devpost_deep_enriched.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; GlobalRevenueBrain/1.5; "
        "+https://github.com/ainetwork-global/AI-Network-Lab-Brain)"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}

PAGE_SUFFIXES = (
    "",
    "details",
    "rules",
    "prizes",
)

MONEY_PATTERNS = [
    re.compile(
        r"(?:total prizes?|prize pool|cash prizes?|awards?|grand prize)"
        r"[^$\d]{0,120}"
        r"(?:US\$|USD|\$)\s*"
        r"(?P<amount>\d[\d,.]*(?:\.\d{1,2})?)"
        r"(?:\s*(?P<suffix>[kKmM]))?",
        re.I,
    ),
    re.compile(
        r"(?:US\$|USD|\$)\s*"
        r"(?P<amount>\d[\d,.]*(?:\.\d{1,2})?)"
        r"(?:\s*(?P<suffix>[kKmM]))?"
        r"[^.\n]{0,120}"
        r"(?:total prizes?|prize pool|cash prizes?|grand prize|in prizes?)",
        re.I,
    ),
]

DATE_PATTERNS = [
    re.compile(
        r"(?:submission deadline|submissions? close|deadline|ends?)"
        r"[\s:–-]{1,10}"
        r"([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}(?:\s+at\s+[^.\n]+)?)",
        re.I,
    ),
    re.compile(
        r"(?:submission deadline|submissions? close|deadline|ends?)"
        r"[\s:–-]{1,10}"
        r"(\d{1,2}/\d{1,2}/\d{4})",
        re.I,
    ),
]

INTERNATIONAL_TERMS = (
    "worldwide",
    "open to all countries",
    "participants from around the world",
    "global participation",
    "international participants",
)

RESTRICTED_TERMS = (
    "united states only",
    "u.s. residents only",
    "residents of the united states",
    "void where prohibited",
)

TEAM_TERMS = (
    "team size",
    "teams of up to",
    "individual or team",
    "form a team",
)

SUBMISSION_TERMS = (
    "submit a project",
    "submission requirements",
    "what to submit",
    "project submission",
    "judging criteria",
)

SPONSOR_TECH_TERMS = (
    "qwen",
    "alibaba cloud",
    "youcam api",
    "gemini",
    "openai",
    "datahub",
    "cockroachdb",
    "aws",
    "arm",
    "backblaze",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean(value: object) -> str:
    return re.sub(
        r"\s+",
        " ",
        html.unescape(str(value or "")),
    ).strip()


def parse_amount(raw: str, suffix: str | None) -> float | None:
    value = raw.replace(",", "")

    try:
        amount = float(value)
    except ValueError:
        return None

    suffix = (suffix or "").lower()

    if suffix == "k":
        amount *= 1_000
    elif suffix == "m":
        amount *= 1_000_000

    return amount if amount > 0 else None


def extract_reward(text: str) -> tuple[float | None, str | None]:
    candidates: list[tuple[float, str]] = []

    for pattern in MONEY_PATTERNS:
        for match in pattern.finditer(text):
            amount = parse_amount(
                match.group("amount"),
                match.groupdict().get("suffix"),
            )

            if amount:
                candidates.append(
                    (
                        amount,
                        clean(match.group(0))[:500],
                    )
                )

    if not candidates:
        return None, None

    amount, evidence = max(candidates, key=lambda item: item[0])
    return amount, evidence


def extract_deadline(text: str) -> tuple[str | None, str | None]:
    for pattern in DATE_PATTERNS:
        match = pattern.search(text)

        if not match:
            continue

        raw = clean(match.group(1))

        try:
            parsed = date_parser.parse(raw, fuzzy=True)
            return parsed.date().isoformat(), raw
        except (ValueError, TypeError, OverflowError):
            return None, raw

    return None, None


def fetch_page(url: str) -> tuple[int, str, str]:
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30,
        allow_redirects=True,
    )

    if response.status_code >= 400:
        return response.status_code, "", response.url

    soup = BeautifulSoup(response.text, "html.parser")

    json_texts = []

    for script in soup.find_all("script"):
        script_type = clean(script.get("type")).lower()
        content = script.string or script.get_text() or ""

        if script_type in {"application/ld+json", "application/json"}:
            try:
                parsed = json.loads(content)
                json_texts.append(
                    json.dumps(parsed, ensure_ascii=False)
                )
            except json.JSONDecodeError:
                pass

    for element in soup(["script", "style", "noscript", "svg"]):
        element.decompose()

    visible_text = clean(soup.get_text(" ", strip=True))
    combined = clean(" ".join([visible_text, *json_texts]))

    return response.status_code, combined[:2_000_000], response.url


def ensure_columns(connection: sqlite3.Connection) -> None:
    columns = {
        row[1]
        for row in connection.execute(
            "PRAGMA table_info(devpost_hackathons)"
        ).fetchall()
    }

    additions = {
        "reward_evidence": "TEXT",
        "deadline_evidence": "TEXT",
        "international_eligibility": "TEXT",
        "team_allowed": "INTEGER",
        "submission_mechanism_confirmed": "INTEGER",
        "sponsor_technology_required": "INTEGER",
        "deep_status": "TEXT",
        "deep_score": "REAL",
        "deep_reason": "TEXT",
        "deep_checked_at": "TEXT",
    }

    for name, data_type in additions.items():
        if name not in columns:
            connection.execute(
                f"ALTER TABLE devpost_hackathons "
                f"ADD COLUMN {name} {data_type}"
            )

    connection.commit()


def classify(row: sqlite3.Row, combined_text: str) -> dict:
    lowered = combined_text.lower()
    reasons: list[str] = []

    reward_amount, reward_evidence = extract_reward(combined_text)
    deadline, deadline_evidence = extract_deadline(combined_text)

    international_allowed = any(
        term in lowered for term in INTERNATIONAL_TERMS
    )
    geographic_restriction = any(
        term in lowered for term in RESTRICTED_TERMS
    )
    team_allowed = any(term in lowered for term in TEAM_TERMS)
    submission_confirmed = any(
        term in lowered for term in SUBMISSION_TERMS
    )
    sponsor_technology_required = any(
        term in lowered for term in SPONSOR_TECH_TERMS
    )

    score = float(row["candidate_score"] or 0)

    if reward_amount:
        score += 20
        reasons.append("Prêmio contextual confirmado na página oficial.")
    else:
        score -= 15
        reasons.append("Prêmio monetário não confirmado.")

    if deadline:
        score += 12
        reasons.append("Prazo de submissão confirmado.")

        try:
            days_remaining = (
                date_parser.parse(deadline).date()
                - datetime.now(timezone.utc).date()
            ).days

            if days_remaining < 0:
                score = 0
                reasons.append("Prazo já encerrado.")
            elif days_remaining < 7:
                score -= 20
                reasons.append("Prazo inferior a sete dias.")
            elif days_remaining >= 21:
                score += 6
        except (ValueError, TypeError):
            pass
    else:
        score -= 8
        reasons.append("Prazo não confirmado.")

    if submission_confirmed:
        score += 12
        reasons.append("Mecanismo de submissão identificado.")
    else:
        score -= 10
        reasons.append("Mecanismo de submissão não confirmado.")

    if international_allowed:
        score += 8
        eligibility = "international_allowed"
        reasons.append("Participação internacional identificada.")
    elif geographic_restriction:
        score -= 35
        eligibility = "geographically_restricted"
        reasons.append("Restrição geográfica identificada.")
    else:
        eligibility = "manual_review"
        reasons.append("Elegibilidade geográfica não confirmada.")

    if team_allowed:
        score += 3

    if sponsor_technology_required:
        reasons.append(
            "Uso de tecnologia do patrocinador pode ser obrigatório."
        )

    score = round(max(0, min(100, score)), 2)

    if score >= 75 and reward_amount and deadline and submission_confirmed:
        deep_status = "deep_actionable"
    elif score >= 50:
        deep_status = "manual_review"
    else:
        deep_status = "deep_rejected"

    return {
        "reward_amount": reward_amount,
        "reward_evidence": reward_evidence,
        "deadline": deadline,
        "deadline_evidence": deadline_evidence,
        "international_eligibility": eligibility,
        "team_allowed": int(team_allowed),
        "submission_mechanism_confirmed": int(submission_confirmed),
        "sponsor_technology_required": int(
            sponsor_technology_required
        ),
        "deep_status": deep_status,
        "deep_score": score,
        "deep_reason": "; ".join(dict.fromkeys(reasons)),
    }


connection = sqlite3.connect(DATABASE)
connection.row_factory = sqlite3.Row
ensure_columns(connection)

rows = connection.execute(
    """
    SELECT *
    FROM devpost_hackathons
    WHERE verification_status = 'staged'
    ORDER BY candidate_score DESC, title
    """
).fetchall()

results = []
errors = 0

print()
print("===== DEVPOST DEEP ENRICHMENT =====")
print(f"Selecionadas: {len(rows)}")

for index, row in enumerate(rows, start=1):
    base_url = row["url"].rstrip("/") + "/"
    texts = []
    pages_checked = []

    print()
    print(f"[{index}/{len(rows)}] {row['title']}")

    for suffix in PAGE_SUFFIXES:
        page_url = (
            base_url
            if not suffix
            else urljoin(base_url, suffix)
        )

        try:
            status, text, final_url = fetch_page(page_url)

            if status < 400 and text:
                texts.append(text)
                pages_checked.append(final_url)

        except Exception as error:
            errors += 1
            print(f"Aviso {page_url}: {error}")

        time.sleep(0.15)

    combined_text = clean(" ".join(texts))
    result = classify(row, combined_text)

    connection.execute(
        """
        UPDATE devpost_hackathons
        SET
            reward_amount = COALESCE(?, reward_amount),
            end_date = COALESCE(?, end_date),
            reward_evidence = ?,
            deadline_evidence = ?,
            international_eligibility = ?,
            team_allowed = ?,
            submission_mechanism_confirmed = ?,
            sponsor_technology_required = ?,
            deep_status = ?,
            deep_score = ?,
            deep_reason = ?,
            deep_checked_at = ?
        WHERE id = ?
        """,
        (
            result["reward_amount"],
            result["deadline"],
            result["reward_evidence"],
            result["deadline_evidence"],
            result["international_eligibility"],
            result["team_allowed"],
            result["submission_mechanism_confirmed"],
            result["sponsor_technology_required"],
            result["deep_status"],
            result["deep_score"],
            result["deep_reason"],
            utc_now(),
            row["id"],
        ),
    )

    connection.commit()

    item = {
        "id": row["id"],
        "title": row["title"],
        "organization": row["organization"],
        "url": row["url"],
        "reward_amount": (
            result["reward_amount"]
            if result["reward_amount"] is not None
            else row["reward_amount"]
        ),
        "reward_currency": row["reward_currency"],
        "end_date": result["deadline"] or row["end_date"],
        "international_eligibility": (
            result["international_eligibility"]
        ),
        "team_allowed": result["team_allowed"],
        "submission_mechanism_confirmed": (
            result["submission_mechanism_confirmed"]
        ),
        "deep_status": result["deep_status"],
        "deep_score": result["deep_score"],
        "deep_reason": result["deep_reason"],
        "pages_checked": " | ".join(pages_checked),
    }

    results.append(item)

    print(f"Status: {item['deep_status']}")
    print(f"Score: {item['deep_score']}")
    print(f"Prêmio: {item['reward_amount']}")
    print(f"Prazo: {item['end_date']}")

results.sort(
    key=lambda item: (
        item["deep_status"] != "deep_actionable",
        -item["deep_score"],
        -(item["reward_amount"] or 0),
    )
)

CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT.parent.mkdir(parents=True, exist_ok=True)

fields = [
    "id",
    "title",
    "organization",
    "url",
    "reward_amount",
    "reward_currency",
    "end_date",
    "international_eligibility",
    "team_allowed",
    "submission_mechanism_confirmed",
    "deep_status",
    "deep_score",
    "deep_reason",
    "pages_checked",
]

with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=fields)
    writer.writeheader()
    writer.writerows(results)

counts = {}

for item in results:
    counts[item["deep_status"]] = (
        counts.get(item["deep_status"], 0) + 1
    )

lines = [
    "# Global Revenue Brain — Devpost Deep Enrichment",
    "",
    f"Gerado em: {utc_now()}",
    "",
    "## Resumo",
    "",
    f"- Total analisado: **{len(results)}**",
    f"- Deep actionable: **{counts.get('deep_actionable', 0)}**",
    f"- Manual review: **{counts.get('manual_review', 0)}**",
    f"- Deep rejected: **{counts.get('deep_rejected', 0)}**",
    f"- Erros de páginas: **{errors}**",
    "",
    "## Ranking",
    "",
]

for index, item in enumerate(results, start=1):
    reward = (
        f"{item['reward_currency'] or 'USD'} "
        f"{float(item['reward_amount']):,.2f}"
        if item["reward_amount"]
        else "não confirmado"
    )

    lines.extend([
        f"### {index}. {item['title']}",
        "",
        f"- Organização: {item['organization']}",
        f"- Status: **{item['deep_status']}**",
        f"- Score: **{item['deep_score']}**",
        f"- Prêmio: {reward}",
        f"- Prazo: {item['end_date'] or 'não confirmado'}",
        f"- Elegibilidade: {item['international_eligibility']}",
        f"- Equipe permitida: {'sim' if item['team_allowed'] else 'não confirmado'}",
        f"- Submissão confirmada: {'sim' if item['submission_mechanism_confirmed'] else 'não'}",
        f"- Motivo: {item['deep_reason']}",
        f"- URL: {item['url']}",
        "",
    ])

REPORT.write_text("\n".join(lines), encoding="utf-8")

print()
print("===== DEVPOST ENRICHMENT SUMMARY =====")
print(f"Analisadas: {len(results)}")
print(f"Deep actionable: {counts.get('deep_actionable', 0)}")
print(f"Manual review: {counts.get('manual_review', 0)}")
print(f"Deep rejected: {counts.get('deep_rejected', 0)}")
print(f"Erros: {errors}")

print()
print("===== DEVPOST DEEP ACTIONABLE =====")

for index, item in enumerate(
    [
        value
        for value in results
        if value["deep_status"] == "deep_actionable"
    ],
    start=1,
):
    print()
    print(f"{index}. {item['title']}")
    print(f"   organização: {item['organization']}")
    print(f"   prêmio: {item['reward_currency']} {item['reward_amount']}")
    print(f"   prazo: {item['end_date']}")
    print(f"   score: {item['deep_score']}")
    print(f"   elegibilidade: {item['international_eligibility']}")
    print(f"   url: {item['url']}")

connection.close()
