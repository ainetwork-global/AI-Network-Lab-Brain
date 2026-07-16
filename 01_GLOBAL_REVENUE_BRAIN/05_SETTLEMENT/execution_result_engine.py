from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "11_DATA" / "global_revenue_brain.db"
REPORT = ROOT / "12_REPORTS" / "LATEST_EXECUTION_RESULTS.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def table_exists(
    connection: sqlite3.Connection,
    table_name: str,
) -> bool:
    result = connection.execute(
        """
        SELECT COUNT(*)
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (table_name,),
    ).fetchone()

    return bool(result[0])


connection = sqlite3.connect(DATABASE)
connection.row_factory = sqlite3.Row

connection.executescript(
    """
    CREATE TABLE IF NOT EXISTS execution_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        candidate_key TEXT NOT NULL UNIQUE,
        title TEXT NOT NULL,
        organization TEXT,
        source_url TEXT NOT NULL,
        repository TEXT,
        issue_number INTEGER,

        reward_announced REAL NOT NULL DEFAULT 0,
        reward_currency TEXT,

        execution_status TEXT
            NOT NULL DEFAULT 'not_started',

        claim_status TEXT
            NOT NULL DEFAULT 'not_claimed',

        submission_status TEXT
            NOT NULL DEFAULT 'not_submitted',

        review_status TEXT
            NOT NULL DEFAULT 'not_reviewed',

        payment_status TEXT
            NOT NULL DEFAULT 'not_expected_yet',

        settlement_target_key TEXT,
        settlement_provider TEXT,
        settlement_rail TEXT,

        amount_approved REAL NOT NULL DEFAULT 0,
        amount_received REAL NOT NULL DEFAULT 0,
        received_currency TEXT,
        received_at TEXT,

        payment_reference TEXT,
        evidence_type TEXT,
        evidence_location TEXT,
        evidence_verified INTEGER
            NOT NULL DEFAULT 0,

        execution_started_at TEXT,
        execution_finished_at TEXT,
        execution_hours REAL NOT NULL DEFAULT 0,

        human_approval_recorded INTEGER
            NOT NULL DEFAULT 0,

        external_action_performed INTEGER
            NOT NULL DEFAULT 0,

        result_notes TEXT,

        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS
    idx_execution_results_payment
    ON execution_results(
        payment_status,
        evidence_verified,
        received_at
    );

    CREATE TABLE IF NOT EXISTS revenue_receipt_ledger (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        execution_result_id INTEGER NOT NULL,
        candidate_key TEXT NOT NULL,

        settlement_target_key TEXT,
        provider TEXT,
        rail TEXT,

        currency TEXT NOT NULL,
        gross_amount REAL NOT NULL,
        fees_amount REAL NOT NULL DEFAULT 0,
        net_amount REAL NOT NULL,

        confirmed_live_revenue INTEGER
            NOT NULL DEFAULT 0,

        transaction_reference TEXT,
        evidence_type TEXT,
        evidence_location TEXT,

        received_at TEXT NOT NULL,
        recorded_at TEXT NOT NULL,

        UNIQUE(
            provider,
            transaction_reference
        )
    );

    CREATE INDEX IF NOT EXISTS
    idx_revenue_receipt_confirmed
    ON revenue_receipt_ledger(
        confirmed_live_revenue,
        received_at
    );
    """
)

now = utc_now()

if table_exists(
    connection,
    "execution_candidate_ranking",
):
    candidates = connection.execute(
        """
        SELECT *
        FROM execution_candidate_ranking
        WHERE rank_position IS NOT NULL
        ORDER BY rank_position
        """
    ).fetchall()

    for candidate in candidates:
        connection.execute(
            """
            INSERT INTO execution_results (
                candidate_key,
                title,
                organization,
                source_url,
                repository,
                issue_number,
                reward_announced,
                reward_currency,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(candidate_key) DO UPDATE SET
                title = excluded.title,
                organization = excluded.organization,
                source_url = excluded.source_url,
                repository = excluded.repository,
                issue_number = excluded.issue_number,
                reward_announced = excluded.reward_announced,
                reward_currency = excluded.reward_currency,
                updated_at = excluded.updated_at
            """,
            (
                candidate["candidate_key"],
                candidate["title"],
                candidate["organization"],
                candidate["source_url"],
                candidate["repository"],
                candidate["issue_number"],
                candidate["reward_amount"] or 0,
                candidate["reward_currency"],
                now,
                now,
            ),
        )

connection.commit()

summary = connection.execute(
    """
    SELECT
        COUNT(*) AS total,
        SUM(
            CASE
                WHEN execution_status = 'in_progress'
                THEN 1 ELSE 0
            END
        ) AS in_progress,
        SUM(
            CASE
                WHEN submission_status = 'submitted'
                THEN 1 ELSE 0
            END
        ) AS submitted,
        SUM(
            CASE
                WHEN review_status = 'accepted'
                THEN 1 ELSE 0
            END
        ) AS accepted,
        SUM(
            CASE
                WHEN payment_status = 'received'
                THEN 1 ELSE 0
            END
        ) AS received,
        SUM(
            CASE
                WHEN payment_status = 'received'
                 AND evidence_verified = 1
                THEN amount_received
                ELSE 0
            END
        ) AS confirmed_value
    FROM execution_results
    """
).fetchone()

ledger = connection.execute(
    """
    SELECT
        COUNT(*) AS receipts,
        COALESCE(SUM(net_amount), 0) AS net_revenue
    FROM revenue_receipt_ledger
    WHERE confirmed_live_revenue = 1
    """
).fetchone()

results = connection.execute(
    """
    SELECT *
    FROM execution_results
    ORDER BY
        CASE payment_status
            WHEN 'received' THEN 1
            WHEN 'approved' THEN 2
            WHEN 'pending' THEN 3
            ELSE 4
        END,
        reward_announced DESC
    LIMIT 30
    """
).fetchall()

lines = [
    "# Global Revenue Brain — Execution Results",
    "",
    f"Gerado em: {utc_now()}",
    "",
    "## Regra de verdade",
    "",
    (
        "Receita só é confirmada quando o pagamento foi realmente "
        "recebido e existe evidência verificada."
    ),
    "",
    "## Resumo",
    "",
    f"- Resultados monitorados: **{summary['total'] or 0}**",
    f"- Em execução: **{summary['in_progress'] or 0}**",
    f"- Submetidos: **{summary['submitted'] or 0}**",
    f"- Aceitos: **{summary['accepted'] or 0}**",
    f"- Pagamentos recebidos: **{summary['received'] or 0}**",
    f"- Valor confirmado: **{summary['confirmed_value'] or 0}**",
    f"- Recibos confirmados: **{ledger['receipts'] or 0}**",
    f"- Receita líquida confirmada: **{ledger['net_revenue'] or 0}**",
    "",
    "## Acompanhamento",
    "",
]

for index, result in enumerate(results, 1):
    lines.extend(
        [
            f"### {index}. {result['title']}",
            "",
            f"- Solicitante: {result['organization']}",
            (
                "- Recompensa anunciada: "
                f"{result['reward_currency']} "
                f"{result['reward_announced']}"
            ),
            f"- Execução: **{result['execution_status']}**",
            f"- Claim: **{result['claim_status']}**",
            f"- Submissão: **{result['submission_status']}**",
            f"- Revisão: **{result['review_status']}**",
            f"- Pagamento: **{result['payment_status']}**",
            (
                "- Evidência verificada: "
                f"{'sim' if result['evidence_verified'] else 'não'}"
            ),
            f"- URL: {result['source_url']}",
            "",
        ]
    )

REPORT.write_text(
    "\n".join(lines),
    encoding="utf-8",
)

print()
print("===== EXECUTION RESULT ENGINE =====")
print("Results monitored:", summary["total"] or 0)
print("In progress:", summary["in_progress"] or 0)
print("Submitted:", summary["submitted"] or 0)
print("Accepted:", summary["accepted"] or 0)
print("Payments received:", summary["received"] or 0)
print("Confirmed received value:", summary["confirmed_value"] or 0)

print()
print("===== CONFIRMED REVENUE LEDGER =====")
print("Confirmed receipts:", ledger["receipts"] or 0)
print("Confirmed net revenue:", ledger["net_revenue"] or 0)

print()
print("===== CURRENT RESULT TRACKING =====")

for result in results[:10]:
    print()
    print("Title:", result["title"])
    print("Execution:", result["execution_status"])
    print("Submission:", result["submission_status"])
    print("Review:", result["review_status"])
    print("Payment:", result["payment_status"])
    print(
        "Evidence verified:",
        bool(result["evidence_verified"]),
    )

connection.close()
