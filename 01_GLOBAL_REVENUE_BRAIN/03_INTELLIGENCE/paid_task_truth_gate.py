from __future__ import annotations

import os
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "11_DATA" / "global_revenue_brain.db"

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()

HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "GlobalRevenueBrain-TruthGate/1.0",
    "X-GitHub-Api-Version": "2022-11-28",
}

if GITHUB_TOKEN:
    HEADERS["Authorization"] = f"Bearer {GITHUB_TOKEN}"


AGGREGATOR_TERMS = (
    "bounty alert",
    "new opportunities found",
    "opportunityies found",
    "bountyscout",
    "bounty scout",
)

NON_TASK_TERMS = (
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


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize(value: object) -> str:
    return re.sub(
        r"\s+",
        " ",
        str(value or ""),
    ).strip().lower()


def table_exists(
    conn: sqlite3.Connection,
    table: str,
) -> bool:
    return bool(
        conn.execute(
            """
            SELECT COUNT(*)
            FROM sqlite_master
            WHERE type='table' AND name=?
            """,
            (table,),
        ).fetchone()[0]
    )


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
        number = int(parts[3])
    except ValueError:
        return None

    return parts[0], parts[1], number


def find_terms(
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
    found = []

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


conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

if not table_exists(conn, "paid_task_execution_queue"):
    raise RuntimeError(
        "Tabela paid_task_execution_queue ausente."
    )

conn.executescript(
    """
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

    CREATE INDEX IF NOT EXISTS idx_verified_paid_tasks_status
    ON verified_paid_tasks(
        truth_status,
        truth_score DESC,
        estimated_value_per_hour DESC
    );
    """
)

candidates = conn.execute(
    """
    SELECT *
    FROM paid_task_execution_queue
    WHERE source = 'github_paid_issues'
      AND execution_status IN (
          'priority_execution_review',
          'standard_execution_review'
      )
    ORDER BY
        execution_score DESC,
        estimated_value_per_hour DESC
    """
).fetchall()

counts: dict[str, int] = {}
processed = 0
errors = 0

print()
print("===== PAID TASK TRUTH GATE =====")
print("Candidates selected:", len(candidates))

for index, row in enumerate(candidates, 1):
    parsed = parse_issue_url(row["url"])

    if parsed is None:
        continue

    owner, repo, issue_number = parsed

    try:
        response = requests.get(
            (
                "https://api.github.com/repos/"
                f"{owner}/{repo}/issues/{issue_number}"
            ),
            headers=HEADERS,
            timeout=30,
        )

        response.raise_for_status()
        issue = response.json()

        if "pull_request" in issue:
            continue

        title = str(issue.get("title") or row["title"])
        body = str(issue.get("body") or "")

        labels = " ".join(
            str(label.get("name") or "")
            for label in (issue.get("labels") or [])
            if isinstance(label, dict)
        )

        text = normalize(
            f"{title} {body} {labels}"
        )

        aggregator_matches = find_terms(
            text,
            AGGREGATOR_TERMS,
        )

        non_task_matches = find_terms(
            text,
            NON_TASK_TERMS,
        )

        payment_matches = find_terms(
            text,
            PAYMENT_TERMS,
        )

        claim_matches = find_terms(
            text,
            CLAIM_TERMS,
        )

        unavailable_matches = find_terms(
            text,
            UNAVAILABLE_TERMS,
        )

        reward, currency, reward_evidence = (
            extract_reward(f"{title}\n{body}")
        )

        state = normalize(
            issue.get("state")
        )

        aggregator = bool(aggregator_matches)
        non_task = bool(non_task_matches)
        payment_found = bool(payment_matches)
        claim_found = bool(claim_matches)
        unavailable = (
            state != "open"
            or bool(unavailable_matches)
        )

        score = 0.0
        reasons = []

        if state == "open":
            score += 20
            reasons.append("Issue aberta.")
        else:
            reasons.append("Issue não está aberta.")

        if reward is not None and reward > 0:
            score += 35
            reasons.append(
                f"Recompensa explícita: {currency} {reward}."
            )
        else:
            reasons.append(
                "Recompensa explícita não encontrada."
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

        if float(row["powershell_fit"] or 0) >= 0.75:
            score += 10

        if aggregator:
            score -= 100
            reasons.append(
                "Agregador detectado."
            )

        if non_task:
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
            truth_status = "rejected_aggregator"
        elif non_task:
            truth_status = "rejected_non_execution"
        elif unavailable:
            truth_status = "rejected_unavailable"
        elif reward is None or reward <= 0:
            truth_status = "reward_evidence_required"
        elif not payment_found:
            truth_status = "payment_terms_review_required"
        elif not claim_found:
            truth_status = "claim_process_review_required"
        elif score >= 85:
            truth_status = "verified_execution_candidate"
        else:
            truth_status = "manual_truth_review"

        estimated_hours = float(
            row["estimated_hours"] or 0
        )

        value_per_hour = (
            round(
                reward / max(estimated_hours, 1),
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
                title = excluded.title,
                organization = excluded.organization,
                github_issue_state = excluded.github_issue_state,
                reward_amount = excluded.reward_amount,
                reward_currency = excluded.reward_currency,
                reward_evidence = excluded.reward_evidence,
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
                estimated_value_per_hour =
                    excluded.estimated_value_per_hour,
                truth_score = excluded.truth_score,
                truth_status = excluded.truth_status,
                truth_reason = excluded.truth_reason,
                verified_at = excluded.verified_at
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
                reward_evidence,
                int(payment_found),
                int(claim_found),
                int(aggregator),
                int(non_task),
                int(unavailable),
                row["powershell_fit"],
                estimated_hours,
                value_per_hour,
                score,
                truth_status,
                "; ".join(reasons),
                utc_now(),
            ),
        )

        counts[truth_status] = (
            counts.get(truth_status, 0) + 1
        )

        processed += 1

        if index % 25 == 0:
            conn.commit()

        time.sleep(0.25)

    except Exception as error:
        errors += 1

        print(
            f"ERROR {owner}/{repo}#{issue_number}: "
            f"{type(error).__name__}: {error}"
        )

conn.commit()

print()
print("===== PAID TASK TRUTH SUMMARY =====")
print("Processed:", processed)

for status, total in sorted(counts.items()):
    print(f"{status}: {total}")

print("Errors:", errors)

print()
print("===== TOP VERIFIED PAID TASKS =====")

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
    LIMIT 20
    """
).fetchall()

for index, row in enumerate(rows, 1):
    print()
    print(f"{index}. {row['title']}")
    print(
        "   repository:",
        f"{row['github_owner']}/"
        f"{row['github_repository']}",
    )
    print(
        "   issue:",
        f"#{row['github_issue_number']}",
    )
    print(
        "   status:",
        row["truth_status"],
    )
    print(
        "   reward:",
        row["reward_currency"],
        row["reward_amount"],
    )
    print(
        "   value/hour:",
        row["estimated_value_per_hour"],
    )
    print(
        "   truth score:",
        row["truth_score"],
    )
    print(
        "   url:",
        row["url"],
    )

conn.close()
