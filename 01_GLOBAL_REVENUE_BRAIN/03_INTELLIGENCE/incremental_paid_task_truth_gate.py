from __future__ import annotations

import json
import os
import re
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "11_DATA" / "global_revenue_brain.db"

REPORT = (
    ROOT
    / "12_REPORTS"
    / "LATEST_INCREMENTAL_PAID_TASK_VALIDATION.md"
)

MODULE_NAME = "incremental_paid_task_truth_gate"

GITHUB_TOKEN = os.getenv(
    "GITHUB_TOKEN",
    "",
).strip()

HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "GlobalRevenueBrain-IncrementalTruthGate/1.0",
    "X-GitHub-Api-Version": "2022-11-28",
}

if GITHUB_TOKEN:
    HEADERS["Authorization"] = f"Bearer {GITHUB_TOKEN}"

# Mantém o consumo baixo quando não há token.
MAX_BATCH = 40 if GITHUB_TOKEN else 10
CACHE_HOURS = 24
REQUEST_DELAY_SECONDS = 1.25 if GITHUB_TOKEN else 3.0

AGGREGATOR_TERMS = (
    "bounty alert",
    "new opportunities found",
    "opportunityies found",
    "bountyscout",
    "bounty scout",
    "opportunity aggregator",
)

NON_EXECUTION_TERMS = (
    "dependency dashboard",
    "renovate dashboard",
    "tracking issue",
    "roadmap",
    "[rfc]",
    "feature request",
    "master plan",
)

PAYMENT_TERMS = (
    "bounty",
    "reward",
    "will pay",
    "paid on completion",
    "payment upon",
    "payout",
    "compensation",
    "fixed price",
)

CLAIM_TERMS = (
    "comment to claim",
    "claim this issue",
    "request assignment",
    "assign yourself",
    "submit a pull request",
    "open a pull request",
    "acceptance criteria",
    "deliverables",
)

UNAVAILABLE_TERMS = (
    "already paid",
    "bounty claimed",
    "winner selected",
    "no longer available",
    "completed by",
)

REWARD_PATTERNS = (
    re.compile(
        r"(?:US\$|USD|\$)\s*(\d+(?:,\d{3})*(?:\.\d+)?)",
        re.I,
    ),
    re.compile(
        r"(\d+(?:,\d{3})*(?:\.\d+)?)\s*USDC",
        re.I,
    ),
    re.compile(
        r"(?:EUR|€)\s*(\d+(?:,\d{3})*(?:\.\d+)?)",
        re.I,
    ),
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_text() -> str:
    return utc_now().isoformat()


def normalize(value: Any) -> str:
    return re.sub(
        r"\s+",
        " ",
        str(value or ""),
    ).strip().lower()


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None

    try:
        result = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )

        if result.tzinfo is None:
            result = result.replace(
                tzinfo=timezone.utc
            )

        return result

    except ValueError:
        return None


def parse_issue_url(
    url: str,
) -> tuple[str, str, int] | None:
    parsed = urlparse(url)

    if parsed.netloc.lower() != "github.com":
        return None

    parts = [
        part
        for part in parsed.path.split("/")
        if part
    ]

    if len(parts) < 4 or parts[2] != "issues":
        return None

    try:
        issue_number = int(parts[3])
    except ValueError:
        return None

    return parts[0], parts[1], issue_number


def contains_any(
    text: str,
    terms: tuple[str, ...],
) -> list[str]:
    return [
        term
        for term in terms
        if term in text
    ]


def extract_reward(
    text: str,
) -> tuple[float | None, str | None, str | None]:
    found: list[
        tuple[float, str, str]
    ] = []

    for pattern in REWARD_PATTERNS:
        for match in pattern.finditer(text):
            evidence = match.group(0)

            try:
                amount = float(
                    match.group(1).replace(",", "")
                )
            except ValueError:
                continue

            upper = evidence.upper()

            if "USDC" in upper:
                currency = "USDC"
            elif "EUR" in upper or "€" in evidence:
                currency = "EUR"
            else:
                currency = "USD"

            found.append(
                (amount, currency, evidence)
            )

    if not found:
        return None, None, None

    found.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    return found[0]


def ensure_schema(
    conn: sqlite3.Connection,
) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS paid_task_api_cache (
            candidate_key TEXT PRIMARY KEY,
            github_owner TEXT NOT NULL,
            github_repository TEXT NOT NULL,
            github_issue_number INTEGER NOT NULL,
            response_json TEXT,
            etag TEXT,
            github_updated_at TEXT,
            fetched_at TEXT,
            http_status INTEGER,
            last_error TEXT
        );

        CREATE TABLE IF NOT EXISTS paid_task_validation_state (
            module_name TEXT PRIMARY KEY,
            paused_until TEXT,
            last_started_at TEXT,
            last_finished_at TEXT,
            last_status TEXT,
            last_message TEXT,
            total_runs INTEGER NOT NULL DEFAULT 0,
            total_validated INTEGER NOT NULL DEFAULT 0,
            total_deferred INTEGER NOT NULL DEFAULT 0,
            total_errors INTEGER NOT NULL DEFAULT 0
        );

        INSERT OR IGNORE INTO paid_task_validation_state (
            module_name
        )
        VALUES (
            'incremental_paid_task_truth_gate'
        );

        CREATE TABLE IF NOT EXISTS verified_paid_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_key TEXT NOT NULL UNIQUE,
            source TEXT NOT NULL,
            title TEXT NOT NULL,
            organization TEXT,
            url TEXT NOT NULL,
            github_owner TEXT,
            github_repository TEXT,
            github_issue_number INTEGER,
            github_issue_state TEXT,
            reward_amount REAL,
            reward_currency TEXT,
            reward_evidence TEXT,
            payment_promise_found INTEGER NOT NULL DEFAULT 0,
            claim_mechanism_found INTEGER NOT NULL DEFAULT 0,
            aggregator_detected INTEGER NOT NULL DEFAULT 0,
            non_execution_detected INTEGER NOT NULL DEFAULT 0,
            unavailable_detected INTEGER NOT NULL DEFAULT 0,
            powershell_fit REAL,
            estimated_hours REAL,
            estimated_value_per_hour REAL,
            truth_score REAL NOT NULL,
            truth_status TEXT NOT NULL,
            truth_reason TEXT NOT NULL,
            human_approval_required INTEGER NOT NULL DEFAULT 1,
            execution_status TEXT NOT NULL DEFAULT 'not_started',
            verified_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_paid_task_cache_fetched
        ON paid_task_api_cache(fetched_at);

        CREATE INDEX IF NOT EXISTS idx_verified_paid_task_truth
        ON verified_paid_tasks(
            truth_status,
            truth_score DESC,
            estimated_value_per_hour DESC
        );
        """
    )

    conn.commit()


def get_pause(
    conn: sqlite3.Connection,
) -> datetime | None:
    row = conn.execute(
        """
        SELECT paused_until
        FROM paid_task_validation_state
        WHERE module_name = ?
        """,
        (MODULE_NAME,),
    ).fetchone()

    if not row:
        return None

    return parse_iso(row[0])


def set_pause(
    conn: sqlite3.Connection,
    pause_until: datetime,
    message: str,
) -> None:
    conn.execute(
        """
        UPDATE paid_task_validation_state
        SET
            paused_until = ?,
            last_status = 'rate_limited',
            last_message = ?,
            total_deferred =
                total_deferred + 1
        WHERE module_name = ?
        """,
        (
            pause_until.isoformat(),
            message,
            MODULE_NAME,
        ),
    )

    conn.commit()


def calculate_pause(
    response: requests.Response,
) -> datetime:
    retry_after = response.headers.get(
        "Retry-After"
    )

    if retry_after:
        try:
            return utc_now() + timedelta(
                seconds=max(
                    int(retry_after),
                    60,
                )
            )
        except ValueError:
            pass

    reset = response.headers.get(
        "X-RateLimit-Reset"
    )

    if reset:
        try:
            return datetime.fromtimestamp(
                int(reset),
                tz=timezone.utc,
            ) + timedelta(minutes=2)
        except ValueError:
            pass

    date_header = response.headers.get("Date")

    if date_header:
        try:
            server_time = parsedate_to_datetime(
                date_header
            )

            return server_time + timedelta(
                minutes=65
            )
        except (TypeError, ValueError):
            pass

    return utc_now() + timedelta(minutes=65)


def cache_is_fresh(
    fetched_at: str | None,
) -> bool:
    parsed = parse_iso(fetched_at)

    if parsed is None:
        return False

    return (
        utc_now() - parsed
    ) < timedelta(hours=CACHE_HOURS)


def fetch_issue(
    conn: sqlite3.Connection,
    candidate_key: str,
    owner: str,
    repo: str,
    issue_number: int,
) -> tuple[
    dict[str, Any] | None,
    str,
    bool,
]:
    cached = conn.execute(
        """
        SELECT
            response_json,
            etag,
            fetched_at
        FROM paid_task_api_cache
        WHERE candidate_key = ?
        """,
        (candidate_key,),
    ).fetchone()

    if cached and cache_is_fresh(cached["fetched_at"]):
        if cached["response_json"]:
            return (
                json.loads(
                    cached["response_json"]
                ),
                "fresh_cache",
                False,
            )

    headers = dict(HEADERS)

    if cached and cached["etag"]:
        headers["If-None-Match"] = cached["etag"]

    url = (
        "https://api.github.com/repos/"
        f"{owner}/{repo}/issues/{issue_number}"
    )

    response = requests.get(
        url,
        headers=headers,
        timeout=30,
    )

    if response.status_code == 304:
        conn.execute(
            """
            UPDATE paid_task_api_cache
            SET
                fetched_at = ?,
                http_status = 304,
                last_error = NULL
            WHERE candidate_key = ?
            """,
            (
                utc_text(),
                candidate_key,
            ),
        )

        conn.commit()

        if cached and cached["response_json"]:
            return (
                json.loads(
                    cached["response_json"]
                ),
                "etag_cache",
                True,
            )

    if response.status_code in (403, 429):
        pause_until = calculate_pause(
            response
        )

        message = (
            f"GitHub rate limit: "
            f"HTTP {response.status_code}; "
            f"retomar após "
            f"{pause_until.isoformat()}"
        )

        set_pause(
            conn,
            pause_until,
            message,
        )

        return None, message, True

    response.raise_for_status()
    issue = response.json()

    conn.execute(
        """
        INSERT INTO paid_task_api_cache (
            candidate_key,
            github_owner,
            github_repository,
            github_issue_number,
            response_json,
            etag,
            github_updated_at,
            fetched_at,
            http_status,
            last_error
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
        ON CONFLICT(candidate_key) DO UPDATE SET
            response_json =
                excluded.response_json,
            etag =
                excluded.etag,
            github_updated_at =
                excluded.github_updated_at,
            fetched_at =
                excluded.fetched_at,
            http_status =
                excluded.http_status,
            last_error = NULL
        """,
        (
            candidate_key,
            owner,
            repo,
            issue_number,
            json.dumps(
                issue,
                ensure_ascii=False,
            ),
            response.headers.get("ETag"),
            issue.get("updated_at"),
            utc_text(),
            response.status_code,
        ),
    )

    conn.commit()

    remaining = response.headers.get(
        "X-RateLimit-Remaining"
    )

    if remaining is not None:
        try:
            if int(remaining) <= 2:
                pause_until = calculate_pause(
                    response
                )

                set_pause(
                    conn,
                    pause_until,
                    (
                        "GitHub rate limit preventivo: "
                        f"remaining={remaining}"
                    ),
                )
        except ValueError:
            pass

    return issue, "github_api", True


def validate_issue(
    conn: sqlite3.Connection,
    row: sqlite3.Row,
    issue: dict[str, Any],
    owner: str,
    repo: str,
    issue_number: int,
) -> str:
    title = str(
        issue.get("title")
        or row["title"]
    )

    body = str(
        issue.get("body")
        or ""
    )

    labels = " ".join(
        str(label.get("name") or "")
        for label in (
            issue.get("labels")
            or []
        )
        if isinstance(label, dict)
    )

    text = normalize(
        f"{title} {body} {labels}"
    )

    aggregator = bool(
        contains_any(
            text,
            AGGREGATOR_TERMS,
        )
    )

    non_execution = bool(
        contains_any(
            text,
            NON_EXECUTION_TERMS,
        )
    )

    payment_found = bool(
        contains_any(
            text,
            PAYMENT_TERMS,
        )
    )

    claim_found = bool(
        contains_any(
            text,
            CLAIM_TERMS,
        )
    )

    unavailable_terms = contains_any(
        text,
        UNAVAILABLE_TERMS,
    )

    state = normalize(
        issue.get("state")
    )

    unavailable = (
        state != "open"
        or bool(unavailable_terms)
    )

    reward, currency, evidence = (
        extract_reward(
            f"{title}\n{body}"
        )
    )

    score = 0.0
    reasons: list[str] = []

    if state == "open":
        score += 20
        reasons.append("Issue aberta.")
    else:
        reasons.append("Issue não está aberta.")

    if reward is not None and reward > 0:
        score += 35
        reasons.append(
            f"Recompensa explícita: "
            f"{currency} {reward}."
        )
    else:
        reasons.append(
            "Recompensa explícita ausente."
        )

    if payment_found:
        score += 20
        reasons.append(
            "Linguagem de pagamento encontrada."
        )
    else:
        reasons.append(
            "Promessa de pagamento não confirmada."
        )

    if claim_found:
        score += 15
        reasons.append(
            "Processo de claim ou entrega encontrado."
        )
    else:
        reasons.append(
            "Processo de claim não confirmado."
        )

    powershell_fit = float(
        row["powershell_fit"]
        or 0
    )

    if powershell_fit >= 0.75:
        score += 10

    if aggregator:
        score -= 100
        reasons.append(
            "Agregador detectado."
        )

    if non_execution:
        score -= 100
        reasons.append(
            "Registro não executável detectado."
        )

    if unavailable:
        score -= 100
        reasons.append(
            "Oportunidade indisponível."
        )

    score = round(
        max(0, min(100, score)),
        2,
    )

    if aggregator:
        status = "rejected_aggregator"
    elif non_execution:
        status = "rejected_non_execution"
    elif unavailable:
        status = "rejected_unavailable"
    elif reward is None or reward <= 0:
        status = "reward_evidence_required"
    elif not payment_found:
        status = "payment_terms_review_required"
    elif not claim_found:
        status = "claim_process_review_required"
    elif score >= 85:
        status = "verified_execution_candidate"
    else:
        status = "manual_truth_review"

    estimated_hours = float(
        row["estimated_hours"]
        or 0
    )

    value_per_hour = (
        round(
            reward
            / max(estimated_hours, 1),
            2,
        )
        if reward is not None
        else 0
    )

    conn.execute(
        """
        INSERT INTO verified_paid_tasks (
            candidate_key,
            source,
            title,
            organization,
            url,
            github_owner,
            github_repository,
            github_issue_number,
            github_issue_state,
            reward_amount,
            reward_currency,
            reward_evidence,
            payment_promise_found,
            claim_mechanism_found,
            aggregator_detected,
            non_execution_detected,
            unavailable_detected,
            powershell_fit,
            estimated_hours,
            estimated_value_per_hour,
            truth_score,
            truth_status,
            truth_reason,
            human_approval_required,
            execution_status,
            verified_at
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1,
            'not_started', ?
        )
        ON CONFLICT(candidate_key) DO UPDATE SET
            title =
                excluded.title,
            github_issue_state =
                excluded.github_issue_state,
            reward_amount =
                excluded.reward_amount,
            reward_currency =
                excluded.reward_currency,
            reward_evidence =
                excluded.reward_evidence,
            payment_promise_found =
                excluded.payment_promise_found,
            claim_mechanism_found =
                excluded.claim_mechanism_found,
            aggregator_detected =
                excluded.aggregator_detected,
            non_execution_detected =
                excluded.non_execution_detected,
            unavailable_detected =
                excluded.unavailable_detected,
            powershell_fit =
                excluded.powershell_fit,
            estimated_hours =
                excluded.estimated_hours,
            estimated_value_per_hour =
                excluded.estimated_value_per_hour,
            truth_score =
                excluded.truth_score,
            truth_status =
                excluded.truth_status,
            truth_reason =
                excluded.truth_reason,
            verified_at =
                excluded.verified_at
        """,
        (
            row["candidate_key"],
            row["source"],
            title,
            row["organization"],
            row["url"],
            owner,
            repo,
            issue_number,
            state,
            reward,
            currency,
            evidence,
            int(payment_found),
            int(claim_found),
            int(aggregator),
            int(non_execution),
            int(unavailable),
            powershell_fit,
            estimated_hours,
            value_per_hour,
            score,
            status,
            "; ".join(reasons),
            utc_text(),
        ),
    )

    conn.commit()

    return status


def write_report(
    conn: sqlite3.Connection,
    *,
    processed: int,
    api_calls: int,
    cache_hits: int,
    deferred: bool,
    message: str,
) -> None:
    rows = conn.execute(
        """
        SELECT
            title,
            github_owner,
            github_repository,
            github_issue_number,
            reward_currency,
            reward_amount,
            estimated_value_per_hour,
            truth_score,
            truth_status,
            url
        FROM verified_paid_tasks
        WHERE truth_status IN (
            'verified_execution_candidate',
            'claim_process_review_required',
            'payment_terms_review_required',
            'manual_truth_review'
        )
        ORDER BY
            CASE truth_status
                WHEN 'verified_execution_candidate' THEN 1
                WHEN 'claim_process_review_required' THEN 2
                WHEN 'payment_terms_review_required' THEN 3
                ELSE 4
            END,
            truth_score DESC,
            estimated_value_per_hour DESC
        LIMIT 30
        """
    ).fetchall()

    lines = [
        "# Incremental Paid Task Validation",
        "",
        f"Gerado em: {utc_text()}",
        "",
        "## Execução",
        "",
        f"- Processados: **{processed}**",
        f"- Chamadas à API: **{api_calls}**",
        f"- Cache utilizado: **{cache_hits}**",
        f"- Adiado por limite: "
        f"**{'sim' if deferred else 'não'}**",
        f"- Mensagem: {message}",
        "",
        "## Melhores tarefas",
        "",
    ]

    for index, row in enumerate(rows, 1):
        lines.extend([
            f"### {index}. {row['title']}",
            "",
            f"- Repositório: "
            f"{row['github_owner']}/"
            f"{row['github_repository']}",
            f"- Issue: #{row['github_issue_number']}",
            f"- Status: **{row['truth_status']}**",
            f"- Recompensa: "
            f"{row['reward_currency']} "
            f"{row['reward_amount']}",
            f"- Valor/hora: "
            f"{row['estimated_value_per_hour']}",
            f"- Truth score: "
            f"{row['truth_score']}",
            f"- URL: {row['url']}",
            "",
        ])

    REPORT.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def main() -> int:
    started = utc_now()

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    ensure_schema(conn)

    pause_until = get_pause(conn)

    print()
    print("===== INCREMENTAL PAID TASK VALIDATION =====")
    print("Authenticated:", bool(GITHUB_TOKEN))
    print("Maximum batch:", MAX_BATCH)
    print("Cache hours:", CACHE_HOURS)

    if (
        pause_until is not None
        and pause_until > utc_now()
    ):
        message = (
            "Validação adiada até "
            f"{pause_until.isoformat()}"
        )

        print("Status: deferred_rate_limit")
        print(message)

        write_report(
            conn,
            processed=0,
            api_calls=0,
            cache_hits=0,
            deferred=True,
            message=message,
        )

        conn.close()
        return 0

    conn.execute(
        """
        UPDATE paid_task_validation_state
        SET
            paused_until = NULL,
            last_started_at = ?,
            last_status = 'running',
            total_runs = total_runs + 1
        WHERE module_name = ?
        """,
        (
            started.isoformat(),
            MODULE_NAME,
        ),
    )

    conn.commit()

    # Só considera itens com valor estimado positivo.
    # Itens nunca validados vêm primeiro.
    # Depois, itens cujo cache venceu.
    candidates = conn.execute(
        """
        SELECT
            q.*
        FROM paid_task_execution_queue q
        LEFT JOIN verified_paid_tasks v
          ON v.candidate_key = q.candidate_key
        LEFT JOIN paid_task_api_cache c
          ON c.candidate_key = q.candidate_key
        WHERE q.source = 'github_paid_issues'
          AND q.execution_status IN (
              'priority_execution_review',
              'standard_execution_review'
          )
          AND COALESCE(q.expected_amount, 0) > 0
          AND (
              v.candidate_key IS NULL
              OR c.fetched_at IS NULL
              OR datetime(c.fetched_at)
                 < datetime('now', '-24 hours')
          )
        ORDER BY
            CASE
                WHEN v.candidate_key IS NULL
                THEN 0
                ELSE 1
            END,
            q.expected_amount DESC,
            q.execution_score DESC,
            q.estimated_value_per_hour DESC
        LIMIT ?
        """,
        (MAX_BATCH,),
    ).fetchall()

    print("Candidates selected:", len(candidates))

    processed = 0
    api_calls = 0
    cache_hits = 0
    errors = 0
    deferred = False
    message = "completed"

    status_counts: dict[str, int] = {}

    for row in candidates:
        parsed = parse_issue_url(
            row["url"]
        )

        if parsed is None:
            continue

        owner, repo, issue_number = parsed

        try:
            issue, source, network_used = fetch_issue(
                conn,
                row["candidate_key"],
                owner,
                repo,
                issue_number,
            )

            if source in (
                "fresh_cache",
                "etag_cache",
            ):
                cache_hits += 1

            if network_used:
                api_calls += 1

            if issue is None:
                deferred = True
                message = source
                break

            if "pull_request" in issue:
                continue

            status = validate_issue(
                conn,
                row,
                issue,
                owner,
                repo,
                issue_number,
            )

            status_counts[status] = (
                status_counts.get(status, 0)
                + 1
            )

            processed += 1

            pause_until = get_pause(conn)

            if (
                pause_until is not None
                and pause_until > utc_now()
            ):
                deferred = True
                message = (
                    "Pausa preventiva até "
                    f"{pause_until.isoformat()}"
                )
                break

            if network_used:
                time.sleep(
                    REQUEST_DELAY_SECONDS
                )

        except Exception as error:
            errors += 1

            print(
                f"ERROR {owner}/{repo}#{issue_number}: "
                f"{type(error).__name__}: {error}"
            )

    finished = utc_now()

    run_status = (
        "deferred_rate_limit"
        if deferred
        else (
            "success"
            if errors == 0
            else "partial_success"
        )
    )

    conn.execute(
        """
        UPDATE paid_task_validation_state
        SET
            last_finished_at = ?,
            last_status = ?,
            last_message = ?,
            total_validated =
                total_validated + ?,
            total_errors =
                total_errors + ?
        WHERE module_name = ?
        """,
        (
            finished.isoformat(),
            run_status,
            message,
            processed,
            errors,
            MODULE_NAME,
        ),
    )

    conn.commit()

    write_report(
        conn,
        processed=processed,
        api_calls=api_calls,
        cache_hits=cache_hits,
        deferred=deferred,
        message=message,
    )

    print()
    print("===== INCREMENTAL VALIDATION RESULT =====")
    print("Status:", run_status)
    print("Processed:", processed)
    print("API calls:", api_calls)
    print("Cache hits:", cache_hits)
    print("Errors:", errors)
    print("Deferred:", deferred)

    print()
    print("===== TRUTH STATUS CREATED =====")

    if status_counts:
        for key, total in sorted(
            status_counts.items()
        ):
            print(f"{key}: {total}")
    else:
        print("No new truth records created.")

    print()
    print(
        "Runtime seconds:",
        round(
            (
                finished - started
            ).total_seconds(),
            2,
        ),
    )

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
