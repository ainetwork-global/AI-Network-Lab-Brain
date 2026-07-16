from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "11_DATA" / "global_revenue_brain.db"
REPORT = ROOT / "12_REPORTS" / "LATEST_DEVPOST_INTERNAL_DIAGNOSTIC.md"
RAW_DIR = ROOT / "09_LOGS" / "devpost_internal"

API_URL = "https://devpost.com/api/hackathons"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/150.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/json,"
        "text/plain;q=0.9,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

MONEY_MARKERS = (
    "$",
    "usd",
    "prize",
    "cash",
    "award",
)

DATE_MARKERS = (
    "deadline",
    "submission period",
    "submissions close",
    "ends",
)

PAGE_SUFFIXES = (
    "",
    "details",
    "rules",
    "prizes",
)


def clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def flatten_json(value, prefix=""):
    rows = []

    if isinstance(value, dict):
        for key, item in value.items():
            current = f"{prefix}.{key}" if prefix else str(key)
            rows.extend(flatten_json(item, current))

    elif isinstance(value, list):
        rows.append((prefix, f"LIST[{len(value)}]"))

        for index, item in enumerate(value[:5]):
            rows.extend(flatten_json(item, f"{prefix}[{index}]"))

    else:
        rows.append((prefix, repr(value)[:500]))

    return rows


def request(url: str, **kwargs):
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30,
        allow_redirects=True,
        **kwargs,
    )

    return response


RAW_DIR.mkdir(parents=True, exist_ok=True)
REPORT.parent.mkdir(parents=True, exist_ok=True)

connection = sqlite3.connect(DATABASE)
connection.row_factory = sqlite3.Row

hackathons = connection.execute(
    """
    SELECT
        id,
        title,
        organization,
        url
    FROM devpost_hackathons
    ORDER BY candidate_score DESC, title
    """
).fetchall()

lines = [
    "# Devpost Internal Data Diagnostic",
    "",
    "## API principal",
    "",
]

print()
print("===== DEVPOST API STRUCTURE =====")

api_response = request(
    API_URL,
    params=[
        ("status[]", "open"),
        ("status[]", "upcoming"),
        ("page", 1),
    ],
)

print("HTTP:", api_response.status_code)
print("Content-Type:", api_response.headers.get("Content-Type"))
print("Bytes:", len(api_response.content))
print("Final URL:", api_response.url)

lines.extend([
    f"- HTTP: {api_response.status_code}",
    f"- Content-Type: {api_response.headers.get('Content-Type')}",
    f"- Bytes: {len(api_response.content)}",
    f"- URL final: {api_response.url}",
    "",
])

try:
    api_data = api_response.json()

    api_json_path = RAW_DIR / "api_page_1.json"
    api_json_path.write_text(
        json.dumps(api_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    flattened = flatten_json(api_data)

    for path, value in flattened[:250]:
        print(f"{path}: {value}")

    lines.extend([
        "### Primeiros campos da resposta",
        "",
    ])

    for path, value in flattened[:250]:
        lines.append(f"- `{path}`: `{value}`")

except Exception as error:
    print("Falha ao interpretar JSON:", error)
    lines.append(f"- Falha JSON: {error}")

print()
print("===== DEVPOST PAGE STRUCTURE =====")

lines.extend([
    "",
    "## Páginas dos eventos",
    "",
])

for index, hackathon in enumerate(hackathons, start=1):
    base_url = hackathon["url"].rstrip("/") + "/"

    print()
    print(f"[{index}/{len(hackathons)}] {hackathon['title']}")

    lines.extend([
        f"### {index}. {hackathon['title']}",
        "",
        f"- Organização: {hackathon['organization']}",
        f"- URL base: {hackathon['url']}",
        "",
    ])

    for suffix in PAGE_SUFFIXES:
        page_url = base_url if not suffix else urljoin(base_url, suffix)

        try:
            response = request(page_url)

            content_type = response.headers.get("Content-Type", "")
            raw_text = response.text
            lowered = raw_text.lower()

            soup = BeautifulSoup(raw_text, "html.parser")

            page_title = clean(
                soup.title.get_text(" ", strip=True)
                if soup.title
                else ""
            )

            visible_text = clean(
                soup.get_text(" ", strip=True)
            )

            money_hits = [
                marker
                for marker in MONEY_MARKERS
                if marker in visible_text.lower()
            ]

            date_hits = [
                marker
                for marker in DATE_MARKERS
                if marker in visible_text.lower()
            ]

            script_sources = []

            for script in soup.find_all("script", src=True):
                script_sources.append(
                    urljoin(response.url, script["src"])
                )

            json_scripts = []

            for script in soup.find_all("script"):
                script_type = clean(script.get("type")).lower()
                content = script.string or script.get_text() or ""

                if script_type in {
                    "application/json",
                    "application/ld+json",
                } and content.strip():
                    json_scripts.append(content[:5000])

            slug = re.sub(
                r"[^a-z0-9]+",
                "-",
                f"{index}-{suffix or 'home'}".lower(),
            ).strip("-")

            raw_path = RAW_DIR / f"{slug}.html"
            raw_path.write_text(raw_text, encoding="utf-8")

            print()
            print(f"  Página: {suffix or 'home'}")
            print(f"  HTTP: {response.status_code}")
            print(f"  Final URL: {response.url}")
            print(f"  Content-Type: {content_type}")
            print(f"  Bytes: {len(response.content)}")
            print(f"  Title: {page_title}")
            print(f"  Visible chars: {len(visible_text)}")
            print(f"  Money markers: {money_hits}")
            print(f"  Date markers: {date_hits}")
            print(f"  JSON scripts: {len(json_scripts)}")
            print(f"  External scripts: {len(script_sources)}")

            lines.extend([
                f"#### {suffix or 'home'}",
                "",
                f"- HTTP: {response.status_code}",
                f"- URL final: {response.url}",
                f"- Content-Type: {content_type}",
                f"- Bytes: {len(response.content)}",
                f"- Título: {page_title}",
                f"- Caracteres visíveis: {len(visible_text)}",
                f"- Marcadores financeiros: {', '.join(money_hits) or 'nenhum'}",
                f"- Marcadores de prazo: {', '.join(date_hits) or 'nenhum'}",
                f"- Scripts JSON: {len(json_scripts)}",
                f"- Scripts externos: {len(script_sources)}",
                f"- Arquivo bruto local: {raw_path}",
                "",
                "Trecho visível:",
                "",
                f"> {visible_text[:1000]}",
                "",
            ])

            if json_scripts:
                json_path = RAW_DIR / f"{slug}-embedded-json.txt"
                json_path.write_text(
                    "\n\n--- JSON SCRIPT ---\n\n".join(json_scripts),
                    encoding="utf-8",
                )

        except Exception as error:
            print(f"  ERRO {page_url}: {error}")

            lines.extend([
                f"#### {suffix or 'home'}",
                "",
                f"- Erro: {error}",
                "",
            ])

REPORT.write_text("\n".join(lines), encoding="utf-8")
connection.close()

print()
print("===== DEVPOST INTERNAL SUMMARY =====")
print(f"Hackathons analisados: {len(hackathons)}")
print(f"Arquivos brutos: {RAW_DIR}")
print(f"Relatório: {REPORT}")
