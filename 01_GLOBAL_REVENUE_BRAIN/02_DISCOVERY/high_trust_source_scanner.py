from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "01_CONFIG" / "high_trust_sources.json"
DATABASE = ROOT / "11_DATA" / "global_revenue_brain.db"
REPORT = ROOT / "12_REPORTS" / "LATEST_HIGH_TRUST_SOURCE_SCAN.md"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; GlobalRevenueBrain/1.0; "
        "+https://github.com/ainetwork-global/AI-Network-Lab-Brain)"
    ),
    "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
}

TERMINAL_NEGATIVE_TERMS = (
    "submissions closed",
    "registration closed",
    "completed audit",
    "completed competition",
    "completed competitions",
    "past audit",
    "past contest",
    "practice competition",
    "beginner practice",
    "intermediate practice",
    "advanced practice",
    "benchmark",
)

GENERIC_NEGATIVE_TERMS = (
    "blog",
    "news",
    "about",
    "privacy",
    "terms of service",
    "cookie",
    "login",
    "sign in",
    "contact",
    "documentation",
    "help center",
)

MONEY_PATTERN = re.compile(
    r"(?:US\$|USD|\$|USDC|USDT|EUR|€|GBP|£)\s*"
    r"\d[\d,.]*(?:\s*[kKmM])?",
    re.IGNORECASE,
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def candidate_key(source: str, url: str) -> str:
    raw = f"{source}|{url}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def valid_domain(url: str, allowed_domains: list[str]) -> bool:
    hostname = (urlparse(url).hostname or "").lower()

    return any(
        hostname == domain.lower()
        or hostname.endswith("." + domain.lower())
        for domain in allowed_domains
    )


def initialize_database(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS high_trust_candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_key TEXT NOT NULL UNIQUE,
            source_name TEXT NOT NULL,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            excerpt TEXT,
            detected_reward_text TEXT,
            candidate_score REAL NOT NULL,
            source_status TEXT NOT NULL,
            official_domain INTEGER NOT NULL DEFAULT 1,
            verification_status TEXT NOT NULL DEFAULT 'staged',
            discovered_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_high_trust_candidates_score
        ON high_trust_candidates(candidate_score DESC);

        CREATE INDEX IF NOT EXISTS idx_high_trust_candidates_source
        ON high_trust_candidates(source_name);

        CREATE TABLE IF NOT EXISTS high_trust_scan_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            sources_checked INTEGER NOT NULL DEFAULT 0,
            sources_healthy INTEGER NOT NULL DEFAULT 0,
            links_examined INTEGER NOT NULL DEFAULT 0,
            candidates_staged INTEGER NOT NULL DEFAULT 0,
            errors INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'running'
        );
        """
    )
    connection.commit()


def score_candidate(
    title: str,
    excerpt: str,
    url: str,
    source: dict,
) -> tuple[float, str | None]:
    combined = f"{title} {excerpt} {url}".lower()

    terminal_terms = tuple(TERMINAL_NEGATIVE_TERMS) + tuple(
        term.lower()
        for term in source.get("reject_terms", [])
    )

    if any(term in combined for term in terminal_terms):
        return 0.0, None

    score = 25.0

    positive_matches = [
        term
        for term in source["positive_terms"]
        if term.lower() in combined
    ]

    score += min(40, len(positive_matches) * 10)

    required_paths = source.get("required_path_terms", [])

    if required_paths and any(
        term.lower() in url.lower()
        for term in required_paths
    ):
        score += 15

    money_match = MONEY_PATTERN.search(f"{title} {excerpt}")

    if money_match:
        score += 20
        reward_text = money_match.group(0)
    else:
        reward_text = None

    negative_matches = [
        term
        for term in GENERIC_NEGATIVE_TERMS
        if term in combined
    ]

    score -= min(40, len(negative_matches) * 12)

    if len(title) < 8:
        score -= 15

    return round(max(0, min(100, score)), 2), reward_text


def fetch_source(source: dict, timeout: int, maximum_links: int):
    response = requests.get(
        source["url"],
        headers=HEADERS,
        timeout=timeout,
        allow_redirects=True,
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    for element in soup(["script", "style", "noscript", "svg"]):
        element.decompose()

    candidates = []
    seen_urls = set()

    for anchor in soup.find_all("a", href=True):
        raw_url = clean(anchor.get("href"))

        if not raw_url:
            continue

        absolute_url = urljoin(response.url, raw_url)
        absolute_url = urldefrag(absolute_url)[0]

        if absolute_url in seen_urls:
            continue

        if not valid_domain(
            absolute_url,
            source["allowed_domains"],
        ):
            continue

        title = clean(anchor.get_text(" ", strip=True))

        parent_text = ""

        if anchor.parent:
            parent_text = clean(
                anchor.parent.get_text(" ", strip=True)
            )[:800]

        score, reward_text = score_candidate(
            title,
            parent_text,
            absolute_url,
            source,
        )

        seen_urls.add(absolute_url)

        candidates.append(
            {
                "title": title or absolute_url,
                "url": absolute_url,
                "excerpt": parent_text,
                "reward_text": reward_text,
                "score": score,
            }
        )

        if len(candidates) >= maximum_links:
            break

    return response.status_code, candidates


config = json.loads(CONFIG.read_text(encoding="utf-8-sig"))
policy = config["policy"]

connection = sqlite3.connect(DATABASE)
connection.row_factory = sqlite3.Row
initialize_database(connection)

run_cursor = connection.execute(
    """
    INSERT INTO high_trust_scan_runs (
        started_at,
        sources_checked,
        status
    )
    VALUES (?, ?, 'running')
    """,
    (now_iso(), len(config["sources"])),
)

run_id = run_cursor.lastrowid

# Only candidates observed and qualified in the current scan remain staged.
# This prevents closed or removed opportunities from persisting indefinitely.
connection.execute(
    """
    UPDATE high_trust_candidates
    SET verification_status = 'stale'
    WHERE verification_status = 'staged'
    """
)
connection.commit()

source_results = []
total_examined = 0
total_staged = 0
healthy_sources = 0
errors = 0

print()
print("===== HIGH TRUST SOURCE SCAN =====")

for source in config["sources"]:
    print()
    print(f"Fonte: {source['name']}")
    print(f"URL: {source['url']}")

    try:
        http_status, candidates = fetch_source(
            source,
            int(policy["request_timeout_seconds"]),
            int(policy["maximum_links_per_source"]),
        )

        healthy_sources += 1
        total_examined += len(candidates)

        qualified = [
            candidate
            for candidate in candidates
            if candidate["score"]
            >= float(policy["minimum_candidate_score"])
        ]

        for candidate in qualified:
            key = candidate_key(
                source["name"],
                candidate["url"],
            )

            connection.execute(
                """
                INSERT INTO high_trust_candidates (
                    candidate_key,
                    source_name,
                    category,
                    title,
                    url,
                    excerpt,
                    detected_reward_text,
                    candidate_score,
                    source_status,
                    official_domain,
                    verification_status,
                    discovered_at,
                    last_seen_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 'staged', ?, ?)
                ON CONFLICT(candidate_key) DO UPDATE SET
                    title = excluded.title,
                    excerpt = excluded.excerpt,
                    detected_reward_text = excluded.detected_reward_text,
                    candidate_score = excluded.candidate_score,
                    source_status = excluded.source_status,
                    verification_status = 'staged',
                    last_seen_at = excluded.last_seen_at
                """,
                (
                    key,
                    source["name"],
                    source["category"],
                    candidate["title"],
                    candidate["url"],
                    candidate["excerpt"],
                    candidate["reward_text"],
                    candidate["score"],
                    f"http_{http_status}",
                    now_iso(),
                    now_iso(),
                ),
            )

        connection.commit()
        total_staged += len(qualified)

        source_results.append(
            {
                "name": source["name"],
                "http_status": http_status,
                "examined": len(candidates),
                "qualified": len(qualified),
                "error": None,
            }
        )

        print(f"HTTP: {http_status}")
        print(f"Links examinados: {len(candidates)}")
        print(f"Candidatos staged: {len(qualified)}")

    except Exception as error:
        errors += 1

        source_results.append(
            {
                "name": source["name"],
                "http_status": None,
                "examined": 0,
                "qualified": 0,
                "error": str(error),
            }
        )

        print(f"ERRO: {error}")

connection.execute(
    """
    UPDATE high_trust_scan_runs
    SET
        finished_at = ?,
        sources_healthy = ?,
        links_examined = ?,
        candidates_staged = ?,
        errors = ?,
        status = ?
    WHERE id = ?
    """,
    (
        now_iso(),
        healthy_sources,
        total_examined,
        total_staged,
        errors,
        "completed" if errors == 0 else "completed_with_errors",
        run_id,
    ),
)
connection.commit()

top_candidates = connection.execute(
    """
    SELECT *
    FROM high_trust_candidates
    WHERE verification_status = 'staged'
    ORDER BY candidate_score DESC, source_name, title
    LIMIT 50
    """
).fetchall()

lines = [
    "# Global Revenue Brain — High-Trust Source Scan",
    "",
    f"Gerado em: {now_iso()}",
    "",
    "## Resumo",
    "",
    f"- Fontes verificadas: **{len(config['sources'])}**",
    f"- Fontes saudáveis: **{healthy_sources}**",
    f"- Links examinados: **{total_examined}**",
    f"- Candidatos staged: **{total_staged}**",
    f"- Erros: **{errors}**",
    "",
    "## Saúde das fontes",
    "",
]

for result in source_results:
    lines.extend(
        [
            f"### {result['name']}",
            "",
            f"- HTTP: {result['http_status']}",
            f"- Links examinados: {result['examined']}",
            f"- Candidatos qualificados: {result['qualified']}",
            f"- Erro: {result['error'] or 'nenhum'}",
            "",
        ]
    )

lines.extend(
    [
        "## Top candidatos isolados",
        "",
    ]
)

for index, row in enumerate(top_candidates, 1):
    lines.extend(
        [
            f"### {index}. {row['title']}",
            "",
            f"- Fonte: {row['source_name']}",
            f"- Categoria: {row['category']}",
            f"- Score inicial: {row['candidate_score']}",
            f"- Recompensa detectada: "
            f"{row['detected_reward_text'] or 'não detectada'}",
            f"- Status: {row['verification_status']}",
            f"- URL: {row['url']}",
            "",
        ]
    )

REPORT.write_text("\n".join(lines), encoding="utf-8")

print()
print("===== HIGH TRUST SUMMARY =====")
print(f"Fontes verificadas: {len(config['sources'])}")
print(f"Fontes saudáveis: {healthy_sources}")
print(f"Links examinados: {total_examined}")
print(f"Candidatos staged: {total_staged}")
print(f"Erros: {errors}")

print()
print("===== TOP 20 STAGED CANDIDATES =====")

for index, row in enumerate(top_candidates[:20], 1):
    print()
    print(f"{index}. {row['title']}")
    print(f"   fonte: {row['source_name']}")
    print(f"   categoria: {row['category']}")
    print(f"   score: {row['candidate_score']}")
    print(
        f"   recompensa: "
        f"{row['detected_reward_text'] or 'não detectada'}"
    )
    print(f"   url: {row['url']}")

connection.close()
