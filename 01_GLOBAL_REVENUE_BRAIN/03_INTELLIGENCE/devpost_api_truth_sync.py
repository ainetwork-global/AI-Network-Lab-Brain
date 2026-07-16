from __future__ import annotations

import csv
import html
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "11_DATA" / "global_revenue_brain.db"
CSV_PATH = ROOT / "04_OPPORTUNITIES" / "devpost_api_verified.csv"
REPORT = ROOT / "12_REPORTS" / "LATEST_DEVPOST_API_TRUTH.md"

API_URL = "https://devpost.com/api/hackathons"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; GlobalRevenueBrain/1.6; "
        "+https://github.com/ainetwork-global/AI-Network-Lab-Brain)"
    ),
    "Accept": "application/json",
}

AI_TERMS = (
    "artificial intelligence",
    "machine learning",
    "ai",
    "agent",
    "agents",
    "automation",
    "api",
    "cloud",
    "database",
    "devops",
    "productivity",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean(value: object) -> str:
    return re.sub(
        r"\s+",
        " ",
        html.unescape(str(value or "")),
    ).strip()


def strip_html(value: object) -> str:
    return clean(
        BeautifulSoup(
            str(value or ""),
            "html.parser",
        ).get_text(" ", strip=True)
    )


def parse_money(value: object) -> float | None:
    text = strip_html(value)

    match = re.search(
        r"(?:US\$|USD|\$)?\s*(\d[\d,.]*(?:\.\d{1,2})?)",
        text,
        re.I,
    )

    if not match:
        return None

    raw = match.group(1).replace(",", "")

    try:
        amount = float(raw)
    except ValueError:
        return None

    return amount if amount > 0 else None


def parse_submission_dates(value: object) -> tuple[str | None, str | None]:
    text = clean(value)

    if not text:
        return None, None

    year_match = re.search(r"\b(20\d{2})\b", text)

    if not year_match:
        return None, None

    year = int(year_match.group(1))

    range_match = re.search(
        r"([A-Za-z]{3,9})\s+(\d{1,2})\s*-\s*"
        r"(?:(?:([A-Za-z]{3,9})\s+)?(\d{1,2})),?\s+"
        r"(20\d{2})",
        text,
    )

    if range_match:
        start_month = range_match.group(1)
        start_day = range_match.group(2)
        end_month = range_match.group(3) or start_month
        end_day = range_match.group(4)
        parsed_year = range_match.group(5)

        try:
            start_date = date_parser.parse(
                f"{start_month} {start_day}, {parsed_year}"
            ).date().isoformat()

            end_date = date_parser.parse(
                f"{end_month} {end_day}, {parsed_year}"
            ).date().isoformat()

            return start_date, end_date
        except (ValueError, TypeError):
            return None, None

    dates = re.findall(
        r"[A-Za-z]{3,9}\s+\d{1,2},?\s+20\d{2}",
        text,
    )

    if dates:
        try:
            parsed = [
                date_parser.parse(item).date().isoformat()
                for item in dates
            ]

            return parsed[0], parsed[-1]
        except (ValueError, TypeError):
            return None, None

    return None, None


def ensure_columns(connection: sqlite3.Connection) -> None:
    columns = {
        row[1]
        for row in connection.execute(
            "PRAGMA table_info(devpost_hackathons)"
        ).fetchall()
    }

    additions = {
        "devpost_id": "INTEGER",
        "time_left_to_submission": "TEXT",
        "cash_prize_count": "INTEGER",
        "other_prize_count": "INTEGER",
        "submission_gallery_url": "TEXT",
        "start_submission_url": "TEXT",
        "invite_only": "INTEGER",
        "managed_by_devpost": "INTEGER",
        "winners_announced": "INTEGER",
        "api_open_state": "TEXT",
        "api_truth_status": "TEXT",
        "api_truth_score": "REAL",
        "api_truth_reason": "TEXT",
        "api_synced_at": "TEXT",
    }

    for name, data_type in additions.items():
        if name not in columns:
            connection.execute(
                f"ALTER TABLE devpost_hackathons "
                f"ADD COLUMN {name} {data_type}"
            )

    connection.commit()


def fetch_all_open_hackathons() -> list[dict]:
    results: dict[str, dict] = {}

    for page in range(1, 30):
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

        response.raise_for_status()
        payload = response.json()

        items = payload.get("hackathons") or []

        if not items:
            break

        for item in items:
            url = clean(item.get("url"))

            if url:
                results[url] = item

        meta = payload.get("meta") or {}
        per_page = int(meta.get("per_page") or len(items) or 1)
        total_count = int(meta.get("total_count") or len(results))

        if page * per_page >= total_count:
            break

    return list(results.values())


def classify(item: dict) -> tuple[str, float, str]:
    reasons: list[str] = []
    score = 40.0

    reward = item["reward_amount"]
    deadline = item["end_date"]
    open_state = item["open_state"]
    submission_url = item["start_submission_url"]
    invite_only = item["invite_only"]
    winners_announced = item["winners_announced"]
    online = item["online"]
    themes = item["themes"]

    if open_state == "open":
        score += 20
        reasons.append("Hackathon aberto na API oficial.")
    else:
        score -= 30
        reasons.append(f"Estado atual: {open_state or 'desconhecido'}.")

    if reward:
        score += 20
        reasons.append("Premiação confirmada pela API oficial.")

        if reward >= 100_000:
            score += 8
        elif reward >= 10_000:
            score += 5
    else:
        score -= 15
        reasons.append("Premiação não identificada.")

    if deadline:
        try:
            days_remaining = (
                date_parser.parse(deadline).date()
                - datetime.now(timezone.utc).date()
            ).days

            reasons.append(
                f"Prazo confirmado; restam aproximadamente {days_remaining} dias."
            )

            if days_remaining < 0:
                score = 0
                reasons.append("Prazo encerrado.")
            elif days_remaining < 5:
                score -= 20
                reasons.append("Prazo muito curto.")
            elif days_remaining >= 14:
                score += 8
        except (ValueError, TypeError):
            score -= 5
    else:
        score -= 10
        reasons.append("Prazo não identificado.")

    if submission_url:
        score += 12
        reasons.append("URL oficial de submissão confirmada.")
    else:
        score -= 15
        reasons.append("URL de submissão não identificada.")

    if online:
        score += 5
        reasons.append("Participação online confirmada.")

    if invite_only:
        score -= 40
        reasons.append("Evento restrito por convite.")

    if winners_announced:
        score = 0
        reasons.append("Vencedores já anunciados.")

    theme_text = " ".join(themes).lower()

    if any(term in theme_text for term in AI_TERMS):
        score += 5
        reasons.append("Tema compatível com IA, software ou automação.")

    score = round(max(0, min(100, score)), 2)

    if (
        score >= 75
        and open_state == "open"
        and reward
        and deadline
        and submission_url
        and not invite_only
        and not winners_announced
    ):
        status = "api_actionable"
    elif score >= 50:
        status = "api_manual_review"
    else:
        status = "api_rejected"

    return status, score, "; ".join(dict.fromkeys(reasons))


connection = sqlite3.connect(DATABASE)
connection.row_factory = sqlite3.Row
ensure_columns(connection)

api_items = fetch_all_open_hackathons()

print()
print("===== DEVPOST API TRUTH SYNC =====")
print(f"Registros recebidos da API: {len(api_items)}")

processed = []

for raw in api_items:
    title = clean(raw.get("title"))
    url = clean(raw.get("url"))

    if not title or not url:
        continue

    location_data = raw.get("displayed_location") or {}
    location = clean(location_data.get("location"))
    online = int(
        location_data.get("icon") == "globe"
        or location.lower() == "online"
    )

    reward_amount = parse_money(raw.get("prize_amount"))
    start_date, end_date = parse_submission_dates(
        raw.get("submission_period_dates")
    )

    themes = [
        clean(theme.get("name"))
        for theme in raw.get("themes") or []
        if isinstance(theme, dict) and clean(theme.get("name"))
    ]

    prize_counts = raw.get("prizes_counts") or {}

    normalized = {
        "devpost_id": raw.get("id"),
        "title": title,
        "url": url,
        "organization": clean(raw.get("organization_name")),
        "reward_amount": reward_amount,
        "start_date": start_date,
        "end_date": end_date,
        "location": location,
        "online": online,
        "participants": raw.get("registrations_count"),
        "open_state": clean(raw.get("open_state")).lower(),
        "time_left": clean(raw.get("time_left_to_submission")),
        "cash_prize_count": int(prize_counts.get("cash") or 0),
        "other_prize_count": int(prize_counts.get("other") or 0),
        "submission_gallery_url": clean(
            raw.get("submission_gallery_url")
        ),
        "start_submission_url": clean(
            raw.get("start_a_submission_url")
        ),
        "invite_only": int(bool(raw.get("invite_only"))),
        "managed_by_devpost": int(
            bool(raw.get("managed_by_devpost_badge"))
        ),
        "winners_announced": int(
            bool(raw.get("winners_announced"))
        ),
        "themes": themes,
    }

    status, score, reason = classify(normalized)

    normalized["api_truth_status"] = status
    normalized["api_truth_score"] = score
    normalized["api_truth_reason"] = reason

    connection.execute(
        """
        INSERT INTO devpost_hackathons (
            candidate_key,
            devpost_id,
            title,
            url,
            organization,
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
            time_left_to_submission,
            cash_prize_count,
            other_prize_count,
            submission_gallery_url,
            start_submission_url,
            invite_only,
            managed_by_devpost,
            winners_announced,
            api_open_state,
            api_truth_status,
            api_truth_score,
            api_truth_reason,
            discovered_at,
            last_seen_at,
            api_synced_at
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, 'USD', ?, ?, ?, ?, ?,
            ?, ?, ?, 'staged', ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?
        )
        ON CONFLICT(candidate_key) DO UPDATE SET
            devpost_id = excluded.devpost_id,
            title = excluded.title,
            organization = excluded.organization,
            reward_amount = excluded.reward_amount,
            start_date = excluded.start_date,
            end_date = excluded.end_date,
            location = excluded.location,
            online = excluded.online,
            participants = excluded.participants,
            status = excluded.status,
            skills = excluded.skills,
            candidate_score = excluded.candidate_score,
            time_left_to_submission = excluded.time_left_to_submission,
            cash_prize_count = excluded.cash_prize_count,
            other_prize_count = excluded.other_prize_count,
            submission_gallery_url = excluded.submission_gallery_url,
            start_submission_url = excluded.start_submission_url,
            invite_only = excluded.invite_only,
            managed_by_devpost = excluded.managed_by_devpost,
            winners_announced = excluded.winners_announced,
            api_open_state = excluded.api_open_state,
            api_truth_status = excluded.api_truth_status,
            api_truth_score = excluded.api_truth_score,
            api_truth_reason = excluded.api_truth_reason,
            last_seen_at = excluded.last_seen_at,
            api_synced_at = excluded.api_synced_at
        """,
        (
            f"devpost-api-{normalized['devpost_id']}",
            normalized["devpost_id"],
            normalized["title"],
            normalized["url"],
            normalized["organization"],
            normalized["reward_amount"],
            normalized["start_date"],
            normalized["end_date"],
            normalized["location"],
            normalized["online"],
            normalized["participants"],
            normalized["open_state"],
            ", ".join(normalized["themes"]),
            normalized["api_truth_score"],
            normalized["time_left"],
            normalized["cash_prize_count"],
            normalized["other_prize_count"],
            normalized["submission_gallery_url"],
            normalized["start_submission_url"],
            normalized["invite_only"],
            normalized["managed_by_devpost"],
            normalized["winners_announced"],
            normalized["open_state"],
            normalized["api_truth_status"],
            normalized["api_truth_score"],
            normalized["api_truth_reason"],
            utc_now(),
            utc_now(),
            utc_now(),
        ),
    )

    processed.append(normalized)

connection.commit()

processed.sort(
    key=lambda item: (
        item["api_truth_status"] != "api_actionable",
        -item["api_truth_score"],
        -(item["reward_amount"] or 0),
    )
)

CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT.parent.mkdir(parents=True, exist_ok=True)

fields = [
    "devpost_id",
    "title",
    "organization",
    "url",
    "reward_amount",
    "start_date",
    "end_date",
    "time_left",
    "location",
    "online",
    "participants",
    "cash_prize_count",
    "other_prize_count",
    "submission_gallery_url",
    "start_submission_url",
    "invite_only",
    "managed_by_devpost",
    "winners_announced",
    "open_state",
    "themes",
    "api_truth_status",
    "api_truth_score",
    "api_truth_reason",
]

with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=fields)
    writer.writeheader()

    for item in processed:
        writer.writerow({
            **item,
            "themes": ", ".join(item["themes"]),
        })

counts: dict[str, int] = {}

for item in processed:
    status = item["api_truth_status"]
    counts[status] = counts.get(status, 0) + 1

lines = [
    "# Global Revenue Brain — Devpost API Truth",
    "",
    f"Gerado em: {utc_now()}",
    "",
    "## Resumo",
    "",
    f"- Registros recebidos: **{len(api_items)}**",
    f"- Registros processados: **{len(processed)}**",
    f"- API actionable: **{counts.get('api_actionable', 0)}**",
    f"- API manual review: **{counts.get('api_manual_review', 0)}**",
    f"- API rejected: **{counts.get('api_rejected', 0)}**",
    "",
    "## Ranking",
    "",
]

for index, item in enumerate(processed, 1):
    lines.extend([
        f"### {index}. {item['title']}",
        "",
        f"- Organização: {item['organization']}",
        f"- Status: **{item['api_truth_status']}**",
        f"- Score: **{item['api_truth_score']}**",
        f"- Prêmio total: USD {item['reward_amount'] or 0:,.2f}",
        f"- Período: {item['start_date']} até {item['end_date']}",
        f"- Tempo restante: {item['time_left']}",
        f"- Participantes: {item['participants']}",
        f"- Prêmios em dinheiro: {item['cash_prize_count']}",
        f"- Localização: {item['location']}",
        f"- Submissão: {item['start_submission_url']}",
        f"- Temas: {', '.join(item['themes'])}",
        f"- Motivo: {item['api_truth_reason']}",
        f"- URL: {item['url']}",
        "",
    ])

REPORT.write_text("\n".join(lines), encoding="utf-8")

print()
print("===== DEVPOST API TRUTH SUMMARY =====")
print(f"Processados: {len(processed)}")
print(f"API actionable: {counts.get('api_actionable', 0)}")
print(f"API manual review: {counts.get('api_manual_review', 0)}")
print(f"API rejected: {counts.get('api_rejected', 0)}")

print()
print("===== DEVPOST API ACTIONABLE =====")

for index, item in enumerate(
    [
        value
        for value in processed
        if value["api_truth_status"] == "api_actionable"
    ],
    1,
):
    print()
    print(f"{index}. {item['title']}")
    print(f"   organização: {item['organization']}")
    print(f"   prêmio total: USD {item['reward_amount']}")
    print(f"   prazo: {item['end_date']}")
    print(f"   tempo restante: {item['time_left']}")
    print(f"   participantes: {item['participants']}")
    print(f"   score: {item['api_truth_score']}")
    print(f"   submissão: {item['start_submission_url']}")
    print(f"   url: {item['url']}")

connection.close()
