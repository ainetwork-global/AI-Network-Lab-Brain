from __future__ import annotations

import hashlib
import html
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import feedparser
import requests
from bs4 import BeautifulSoup


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "01_CONFIG" / "hunter_sources.json"
LOG_PATH = PROJECT_ROOT / "09_LOGS" / "scanner_errors.log"

sys.path.insert(0, str(PROJECT_ROOT / "10_SCRIPTS"))
sys.path.insert(0, str(PROJECT_ROOT / "03_INTELLIGENCE"))

from database import connect
from opportunity_scorer import score_opportunity


USER_AGENT = (
    "Global-Revenue-Brain/1.1 "
    "(legitimate-public-opportunity-research)"
)

MONEY_EVIDENCE = re.compile(
    r"(?:US\\$|USD|USDC|EUR|GBP|\\$|€|£)\\s*\\d"
    r"|\\d[\\d,.]*\\s*(?:USD|USDC|EUR|GBP)\\b",
    re.IGNORECASE,
)
PAID_PLATFORM_EVIDENCE = re.compile(
    r"\\b(?:algora|gitcoin|polar\\.sh|bounty)\\b",
    re.IGNORECASE,
)


def has_explicit_reward_evidence(item: dict[str, Any]) -> bool:
    """Keep discovery focused on issues with verifiable payment language."""
    text = " ".join(
        str(item.get(field, "") or "")
        for field in ("title", "body", "html_url")
    )
    return bool(
        MONEY_EVIDENCE.search(text)
        or (
            PAID_PLATFORM_EVIDENCE.search(text)
            and re.search(r"\\b(?:reward|paid|payment|prize)\\b", text, re.I)
        )
    )


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_key(*parts: str) -> str:
    raw = "|".join(parts).encode("utf-8", errors="ignore")
    return hashlib.sha256(raw).hexdigest()


def clean_text(value: str | None, limit: int = 8000) -> str:
    if not value:
        return ""

    soup = BeautifulSoup(html.unescape(str(value)), "html.parser")
    text = soup.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text)

    return text[:limit]


def load_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))


def log_error(source: str, error: Exception | str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    with LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write(
            f"{now_iso()}\t{source}\t{str(error)}\n"
        )


def update_source_health(
    database,
    source_key: str,
    source_name: str,
    source_type: str,
    source_url: str | None,
    success: bool,
    items_found: int,
    error: str | None = None,
) -> None:
    checked_at = now_iso()

    if success:
        database.execute(
            """
            INSERT INTO source_health (
                source_key,
                source_name,
                source_type,
                source_url,
                last_checked_at,
                last_success_at,
                consecutive_errors,
                last_error,
                last_items_found
            )
            VALUES (?, ?, ?, ?, ?, ?, 0, NULL, ?)
            ON CONFLICT(source_key) DO UPDATE SET
                source_name = excluded.source_name,
                source_type = excluded.source_type,
                source_url = excluded.source_url,
                last_checked_at = excluded.last_checked_at,
                last_success_at = excluded.last_success_at,
                consecutive_errors = 0,
                last_error = NULL,
                last_items_found = excluded.last_items_found
            """,
            (
                source_key,
                source_name,
                source_type,
                source_url,
                checked_at,
                checked_at,
                items_found,
            ),
        )
    else:
        database.execute(
            """
            INSERT INTO source_health (
                source_key,
                source_name,
                source_type,
                source_url,
                last_checked_at,
                last_error_at,
                consecutive_errors,
                last_error,
                last_items_found
            )
            VALUES (?, ?, ?, ?, ?, ?, 1, ?, 0)
            ON CONFLICT(source_key) DO UPDATE SET
                last_checked_at = excluded.last_checked_at,
                last_error_at = excluded.last_error_at,
                consecutive_errors = source_health.consecutive_errors + 1,
                last_error = excluded.last_error,
                last_items_found = 0
            """,
            (
                source_key,
                source_name,
                source_type,
                source_url,
                checked_at,
                checked_at,
                error,
            ),
        )


def save_opportunity(database, item: dict[str, Any]) -> str:
    scored = score_opportunity(
        title=item["title"],
        description=item.get("description", ""),
        category=item["category"],
        source_type=item["source_type"],
        source_url=item["source_url"],
    )

    current_time = now_iso()

    existing = database.execute(
        """
        SELECT id
        FROM opportunities
        WHERE opportunity_key = ?
        """,
        (item["opportunity_key"],),
    ).fetchone()

    values = {
        **item,
        **scored,
        "current_time": current_time,
    }

    if existing:
        database.execute(
            """
            UPDATE opportunities
            SET
                title = :title,
                category = :category,
                source_name = :source_name,
                source_type = :source_type,
                source_url = :source_url,
                repository = :repository,
                author = :author,
                description = :description,
                published_at = :published_at,
                last_seen_at = :current_time,
                estimated_value = :estimated_value,
                financial_score = :financial_score,
                confidence_score = :confidence_score,
                automation_score = :automation_score,
                risk_score = :risk_score,
                final_score = :final_score,
                score_reason = :score_reason,
                updated_at = :current_time
            WHERE opportunity_key = :opportunity_key
            """,
            values,
        )

        return "updated"

    database.execute(
        """
        INSERT INTO opportunities (
            opportunity_key,
            title,
            category,
            source_name,
            source_type,
            source_url,
            repository,
            author,
            description,
            published_at,
            discovered_at,
            last_seen_at,
            status,
            currency,
            estimated_value,
            capital_required,
            financial_score,
            confidence_score,
            automation_score,
            risk_score,
            final_score,
            score_reason,
            human_approval_required,
            created_at,
            updated_at
        )
        VALUES (
            :opportunity_key,
            :title,
            :category,
            :source_name,
            :source_type,
            :source_url,
            :repository,
            :author,
            :description,
            :published_at,
            :current_time,
            :current_time,
            'discovered',
            'USD',
            :estimated_value,
            0,
            :financial_score,
            :confidence_score,
            :automation_score,
            :risk_score,
            :final_score,
            :score_reason,
            1,
            :current_time,
            :current_time
        )
        """,
        values,
    )

    return "inserted"


def scan_github(
    database,
    config: dict[str, Any],
) -> dict[str, int]:
    token = os.getenv("GITHUB_TOKEN", "").strip()

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"

    totals = {
        "sources": 0,
        "found": 0,
        "inserted": 0,
        "updated": 0,
        "errors": 0,
    }

    max_results = int(
        config["system"].get("maximum_results_per_query", 30)
    )
    recent_days = max(
        1,
        int(config["system"].get("github_recent_update_days", 45)),
    )
    updated_after = (
        datetime.now(timezone.utc) - timedelta(days=recent_days)
    ).date().isoformat()

    timeout = int(
        config["system"].get("request_timeout_seconds", 20)
    )

    for source in config["github_queries"]:
        totals["sources"] += 1
        query = source["query"]
        if "updated:" not in query:
            query = f"{query} updated:>={updated_after}"
        source_key = build_key("github", source["name"], query)

        try:
            response = requests.get(
                "https://api.github.com/search/issues",
                headers=headers,
                params={
                    "q": query,
                    "sort": "updated",
                    "order": "desc",
                    "per_page": max_results,
                },
                timeout=timeout,
            )

            response.raise_for_status()
            payload = response.json()
            raw_items = payload.get("items", [])
            items = [
                item
                for item in raw_items
                if has_explicit_reward_evidence(item)
                and "pull_request" not in item
            ]

            totals["found"] += len(items)

            for github_item in items:
                repository_url = (
                    github_item.get("repository_url", "")
                )

                repository_parts = repository_url.rstrip("/").split("/")[-2:]
                repository = "/".join(repository_parts)

                item = {
                    "opportunity_key": build_key(
                        "github",
                        str(github_item.get("id", "")),
                        github_item.get("html_url", ""),
                    ),
                    "title": clean_text(
                        github_item.get("title", ""),
                        limit=1000,
                    ),
                    "category": source["category"],
                    "source_name": source["name"],
                    "source_type": "github_api",
                    "source_url": github_item.get("html_url", ""),
                    "repository": repository,
                    "author": (
                        github_item.get("user", {}) or {}
                    ).get("login", ""),
                    "description": clean_text(
                        github_item.get("body", ""),
                        limit=8000,
                    ),
                    "published_at": github_item.get(
                        "created_at", ""
                    ),
                }

                result = save_opportunity(database, item)
                totals[result] += 1

            update_source_health(
                database=database,
                source_key=source_key,
                source_name=source["name"],
                source_type="github_api",
                source_url="https://api.github.com/search/issues",
                success=True,
                items_found=len(items),
            )

            database.commit()

        except Exception as error:
            totals["errors"] += 1
            log_error(source["name"], error)

            update_source_health(
                database=database,
                source_key=source_key,
                source_name=source["name"],
                source_type="github_api",
                source_url="https://api.github.com/search/issues",
                success=False,
                items_found=0,
                error=str(error),
            )

            database.commit()

    return totals


def scan_rss(
    database,
    config: dict[str, Any],
) -> dict[str, int]:
    totals = {
        "sources": 0,
        "found": 0,
        "inserted": 0,
        "updated": 0,
        "errors": 0,
    }

    for source in config["rss_sources"]:
        totals["sources"] += 1
        source_key = build_key("rss", source["name"], source["url"])

        try:
            parsed = feedparser.parse(
                source["url"],
                agent=USER_AGENT,
            )

            if getattr(parsed, "bozo", False) and not parsed.entries:
                raise RuntimeError(
                    str(getattr(parsed, "bozo_exception", "RSS inválido"))
                )

            entries = parsed.entries[:30]
            totals["found"] += len(entries)

            for entry in entries:
                title = clean_text(entry.get("title", ""), limit=1000)
                link = str(entry.get("link", "")).strip()

                if not title or not link:
                    continue

                item = {
                    "opportunity_key": build_key(
                        "rss",
                        source["name"],
                        link,
                        title,
                    ),
                    "title": title,
                    "category": source["category"],
                    "source_name": source["name"],
                    "source_type": "rss",
                    "source_url": link,
                    "repository": "",
                    "author": clean_text(
                        entry.get("author", ""),
                        limit=500,
                    ),
                    "description": clean_text(
                        entry.get(
                            "summary",
                            entry.get("description", ""),
                        ),
                        limit=8000,
                    ),
                    "published_at": str(
                        entry.get(
                            "published",
                            entry.get("updated", ""),
                        )
                    ),
                }

                result = save_opportunity(database, item)
                totals[result] += 1

            update_source_health(
                database=database,
                source_key=source_key,
                source_name=source["name"],
                source_type="rss",
                source_url=source["url"],
                success=True,
                items_found=len(entries),
            )

            database.commit()

        except Exception as error:
            totals["errors"] += 1
            log_error(source["name"], error)

            update_source_health(
                database=database,
                source_key=source_key,
                source_name=source["name"],
                source_type="rss",
                source_url=source["url"],
                success=False,
                items_found=0,
                error=str(error),
            )

            database.commit()

    return totals


def scan_all() -> dict[str, int | str]:
    config = load_config()
    started_at = now_iso()

    totals: dict[str, int | str] = {
        "started_at": started_at,
        "completed_at": "",
        "sources": 0,
        "found": 0,
        "inserted": 0,
        "updated": 0,
        "errors": 0,
    }

    with connect() as database:
        cursor = database.execute(
            """
            INSERT INTO scan_runs (
                started_at,
                status
            )
            VALUES (?, 'running')
            """,
            (started_at,),
        )

        scan_run_id = cursor.lastrowid
        database.commit()

        github_totals = scan_github(database, config)
        rss_totals = scan_rss(database, config)

        for field in [
            "sources",
            "found",
            "inserted",
            "updated",
            "errors",
        ]:
            totals[field] = (
                int(github_totals[field])
                + int(rss_totals[field])
            )

        completed_at = now_iso()
        totals["completed_at"] = completed_at

        final_status = (
            "completed_with_errors"
            if int(totals["errors"]) > 0
            else "completed"
        )

        database.execute(
            """
            UPDATE scan_runs
            SET
                completed_at = ?,
                status = ?,
                sources_checked = ?,
                items_found = ?,
                items_inserted = ?,
                items_updated = ?,
                errors = ?
            WHERE id = ?
            """,
            (
                completed_at,
                final_status,
                totals["sources"],
                totals["found"],
                totals["inserted"],
                totals["updated"],
                totals["errors"],
                scan_run_id,
            ),
        )

        database.commit()

    return totals


if __name__ == "__main__":
    result = scan_all()

    print("")
    print("GLOBAL REVENUE HUNTER — SCAN CONCLUÍDO")
    print("--------------------------------------")
    print(f"Fontes verificadas: {result['sources']}")
    print(f"Itens encontrados: {result['found']}")
    print(f"Novos registros: {result['inserted']}")
    print(f"Registros atualizados: {result['updated']}")
    print(f"Erros de fonte: {result['errors']}")
