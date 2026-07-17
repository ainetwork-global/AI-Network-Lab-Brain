from __future__ import annotations

import math
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

DATABASE = (
    ROOT
    / "11_DATA"
    / "global_revenue_brain.db"
)

REPORT = (
    ROOT
    / "12_REPORTS"
    / "LATEST_REVENUE_LEARNING.md"
)

PROBABILITY_CLASSIFIER = (
    ROOT
    / "03_INTELLIGENCE"
    / "classify_payment_probability.py"
)

EXECUTION_RANKER = (
    ROOT
    / "03_INTELLIGENCE"
    / "execution_candidate_ranking.py"
)


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def table_exists(
    connection: sqlite3.Connection,
    table_name: str,
) -> bool:
    return bool(
        connection.execute(
            """
            SELECT COUNT(*)
            FROM sqlite_master
            WHERE type = 'table'
              AND name = ?
            """,
            (table_name,),
        ).fetchone()[0]
    )


def table_columns(
    connection: sqlite3.Connection,
    table_name: str,
) -> set[str]:
    if not table_exists(
        connection,
        table_name,
    ):
        return set()

    return {
        str(row[1])
        for row in connection.execute(
            f'PRAGMA table_info("{table_name}")'
        ).fetchall()
    }


def clamp(
    value: float,
    minimum: float = 0.0,
    maximum: float = 100.0,
) -> float:
    return max(
        minimum,
        min(maximum, value),
    )


def safe_float(
    value: Any,
) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def wilson_lower_bound(
    successes: float,
    total: float,
    z: float = 1.96,
) -> float:
    if total <= 0:
        return 0.0

    proportion = successes / total

    denominator = (
        1
        + (z * z / total)
    )

    centre = (
        proportion
        + (z * z / (2 * total))
    )

    adjustment = z * math.sqrt(
        (
            proportion
            * (1 - proportion)
            / total
        )
        + (
            z * z
            / (4 * total * total)
        )
    )

    return max(
        0.0,
        (
            centre
            - adjustment
        )
        / denominator,
    )


connection = sqlite3.connect(
    DATABASE
)

connection.row_factory = sqlite3.Row

if not table_exists(
    connection,
    "execution_results",
):
    raise RuntimeError(
        "Tabela execution_results não encontrada. "
        "Execute a Etapa 5 primeiro."
    )

connection.executescript(
    """
    CREATE TABLE IF NOT EXISTS source_reputation (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_name TEXT NOT NULL UNIQUE,

        total_opportunities INTEGER NOT NULL DEFAULT 0,
        total_started INTEGER NOT NULL DEFAULT 0,
        total_submitted INTEGER NOT NULL DEFAULT 0,
        total_accepted INTEGER NOT NULL DEFAULT 0,

        payment_confirmed INTEGER NOT NULL DEFAULT 0,
        payment_failed INTEGER NOT NULL DEFAULT 0,

        avg_reward REAL NOT NULL DEFAULT 0,
        avg_received REAL NOT NULL DEFAULT 0,
        avg_hours REAL NOT NULL DEFAULT 0,

        payment_success_rate REAL NOT NULL DEFAULT 0,
        conservative_success_rate REAL NOT NULL DEFAULT 0,

        payout_speed REAL NOT NULL DEFAULT 0,
        automation_success REAL NOT NULL DEFAULT 0,
        confidence_score REAL NOT NULL DEFAULT 0,
        roi_score REAL NOT NULL DEFAULT 0,

        last_seen TEXT,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS revenue_learning (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        source_name TEXT NOT NULL,
        payment_method TEXT NOT NULL DEFAULT 'unknown',
        category TEXT NOT NULL DEFAULT 'unknown',

        observations INTEGER NOT NULL DEFAULT 0,
        successful_payments INTEGER NOT NULL DEFAULT 0,
        failed_payments INTEGER NOT NULL DEFAULT 0,

        success_rate REAL NOT NULL DEFAULT 0,
        conservative_success_rate REAL NOT NULL DEFAULT 0,

        avg_reward REAL NOT NULL DEFAULT 0,
        avg_received REAL NOT NULL DEFAULT 0,
        avg_hours REAL NOT NULL DEFAULT 0,

        roi_score REAL NOT NULL DEFAULT 0,
        confidence REAL NOT NULL DEFAULT 0,

        updated_at TEXT NOT NULL,

        UNIQUE(
            source_name,
            payment_method,
            category
        )
    );

    CREATE TABLE IF NOT EXISTS revenue_feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        candidate_key TEXT NOT NULL UNIQUE,
        opportunity_url TEXT,
        source_name TEXT,
        category TEXT,

        execution_result TEXT,
        reward_received REAL NOT NULL DEFAULT 0,
        payment_currency TEXT,
        payment_method TEXT,

        execution_hours REAL NOT NULL DEFAULT 0,
        roi REAL NOT NULL DEFAULT 0,
        automation_level REAL NOT NULL DEFAULT 0,

        paid INTEGER NOT NULL DEFAULT 0,
        evidence_verified INTEGER NOT NULL DEFAULT 0,

        confidence_before REAL NOT NULL DEFAULT 0,
        confidence_after REAL NOT NULL DEFAULT 0,

        learned INTEGER NOT NULL DEFAULT 0,

        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS learning_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at TEXT NOT NULL,
        finished_at TEXT,
        results_analyzed INTEGER NOT NULL DEFAULT 0,
        sources_updated INTEGER NOT NULL DEFAULT 0,
        feedback_updated INTEGER NOT NULL DEFAULT 0,
        confirmed_payments INTEGER NOT NULL DEFAULT 0,
        confirmed_revenue REAL NOT NULL DEFAULT 0,
        status TEXT NOT NULL,
        notes TEXT
    );

    CREATE INDEX IF NOT EXISTS
    idx_source_reputation_roi
    ON source_reputation(
        roi_score DESC,
        confidence_score DESC
    );

    CREATE INDEX IF NOT EXISTS
    idx_revenue_learning_roi
    ON revenue_learning(
        roi_score DESC,
        confidence DESC
    );

    CREATE INDEX IF NOT EXISTS
    idx_revenue_feedback_paid
    ON revenue_feedback(
        paid,
        evidence_verified,
        learned
    );
    """
)

started_at = utc_now()

cursor = connection.execute(
    """
    INSERT INTO learning_runs (
        started_at,
        status
    )
    VALUES (?, 'running')
    """,
    (started_at,),
)

run_id = cursor.lastrowid
connection.commit()

results = connection.execute(
    """
    SELECT *
    FROM execution_results
    """
).fetchall()

print()
print("===== REVENUE LEARNING ENGINE =====")
print("Execution results analyzed:", len(results))

source_groups: dict[
    str,
    list[sqlite3.Row],
] = {}

feedback_updated = 0
confirmed_payments = 0
confirmed_revenue = 0.0
now = utc_now()

ranking_columns = table_columns(
    connection,
    "execution_candidate_ranking",
)

for result in results:
    source_name = str(
        result["organization"]
        or "unknown"
    ).strip()

    source_groups.setdefault(
        source_name,
        [],
    ).append(result)

    payment_received = (
        str(
            result["payment_status"]
            or ""
        ).lower()
        == "received"
    )

    evidence_verified = bool(
        result["evidence_verified"]
    )

    paid = int(
        payment_received
        and evidence_verified
        and safe_float(
            result["amount_received"]
        ) > 0
    )

    amount_received = (
        safe_float(
            result["amount_received"]
        )
        if paid
        else 0.0
    )

    if paid:
        confirmed_payments += 1
        confirmed_revenue += amount_received

    execution_hours = safe_float(
        result["execution_hours"]
    )

    roi = (
        amount_received
        / max(execution_hours, 1.0)
        if paid
        else 0.0
    )

    confidence_before = 0.0

    if (
        table_exists(
            connection,
            "execution_candidate_ranking",
        )
        and "candidate_key" in ranking_columns
    ):
        ranking = connection.execute(
            """
            SELECT payment_probability
            FROM execution_candidate_ranking
            WHERE candidate_key = ?
            LIMIT 1
            """,
            (
                result["candidate_key"],
            ),
        ).fetchone()

        if ranking:
            confidence_before = safe_float(
                ranking["payment_probability"]
            )

    if paid:
        confidence_after = clamp(
            confidence_before
            + (
                100
                - confidence_before
            )
            * 0.35
        )

        execution_result = (
            "confirmed_paid"
        )

    elif (
        str(
            result["payment_status"]
            or ""
        ).lower()
        in {
            "failed",
            "rejected",
            "cancelled",
            "not_paid",
        }
    ):
        confidence_after = clamp(
            confidence_before
            * 0.60
        )

        execution_result = (
            "confirmed_not_paid"
        )

    elif (
        str(
            result["review_status"]
            or ""
        ).lower()
        == "rejected"
    ):
        confidence_after = clamp(
            confidence_before
            * 0.75
        )

        execution_result = (
            "submission_rejected"
        )

    else:
        confidence_after = (
            confidence_before
        )

        execution_result = (
            str(
                result["execution_status"]
                or "not_started"
            )
        )

    payment_method = str(
        result["settlement_target_key"]
        or result["settlement_provider"]
        or result["settlement_rail"]
        or "unknown"
    )

    connection.execute(
        """
        INSERT INTO revenue_feedback (
            candidate_key,
            opportunity_url,
            source_name,
            category,
            execution_result,
            reward_received,
            payment_currency,
            payment_method,
            execution_hours,
            roi,
            automation_level,
            paid,
            evidence_verified,
            confidence_before,
            confidence_after,
            learned,
            created_at,
            updated_at
        )
        VALUES (
            ?, ?, ?, 'paid_online_task', ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, 1, ?, ?
        )
        ON CONFLICT(candidate_key) DO UPDATE SET
            opportunity_url =
                excluded.opportunity_url,
            source_name =
                excluded.source_name,
            execution_result =
                excluded.execution_result,
            reward_received =
                excluded.reward_received,
            payment_currency =
                excluded.payment_currency,
            payment_method =
                excluded.payment_method,
            execution_hours =
                excluded.execution_hours,
            roi =
                excluded.roi,
            automation_level =
                excluded.automation_level,
            paid =
                excluded.paid,
            evidence_verified =
                excluded.evidence_verified,
            confidence_before =
                excluded.confidence_before,
            confidence_after =
                excluded.confidence_after,
            learned = 1,
            updated_at =
                excluded.updated_at
        """,
        (
            result["candidate_key"],
            result["source_url"],
            source_name,
            execution_result,
            amount_received,
            (
                result["received_currency"]
                or result["reward_currency"]
            ),
            payment_method,
            execution_hours,
            roi,
            1.0,
            paid,
            int(evidence_verified),
            confidence_before,
            confidence_after,
            now,
            now,
        ),
    )

    feedback_updated += 1

sources_updated = 0

for source_name, source_results in source_groups.items():
    total = len(source_results)

    started = sum(
        1
        for item in source_results
        if str(
            item["execution_status"]
            or ""
        ).lower()
        not in {
            "",
            "not_started",
        }
    )

    submitted = sum(
        1
        for item in source_results
        if str(
            item["submission_status"]
            or ""
        ).lower()
        == "submitted"
    )

    accepted = sum(
        1
        for item in source_results
        if str(
            item["review_status"]
            or ""
        ).lower()
        == "accepted"
    )

    paid_results = [
        item
        for item in source_results
        if (
            str(
                item["payment_status"]
                or ""
            ).lower()
            == "received"
            and bool(
                item["evidence_verified"]
            )
            and safe_float(
                item["amount_received"]
            )
            > 0
        )
    ]

    confirmed = len(
        paid_results
    )

    failed = sum(
        1
        for item in source_results
        if str(
            item["payment_status"]
            or ""
        ).lower()
        in {
            "failed",
            "rejected",
            "cancelled",
            "not_paid",
        }
    )

    observed_outcomes = (
        confirmed
        + failed
    )

    success_rate = (
        confirmed
        / observed_outcomes
        if observed_outcomes > 0
        else 0.0
    )

    conservative_rate = (
        wilson_lower_bound(
            confirmed,
            observed_outcomes,
        )
        if observed_outcomes > 0
        else 0.0
    )

    announced_values = [
        safe_float(
            item["reward_announced"]
        )
        for item in source_results
        if safe_float(
            item["reward_announced"]
        ) > 0
    ]

    received_values = [
        safe_float(
            item["amount_received"]
        )
        for item in paid_results
    ]

    hours_values = [
        safe_float(
            item["execution_hours"]
        )
        for item in source_results
        if safe_float(
            item["execution_hours"]
        ) > 0
    ]

    avg_reward = (
        sum(announced_values)
        / len(announced_values)
        if announced_values
        else 0.0
    )

    avg_received = (
        sum(received_values)
        / len(received_values)
        if received_values
        else 0.0
    )

    avg_hours = (
        sum(hours_values)
        / len(hours_values)
        if hours_values
        else 0.0
    )

    avg_roi = (
        avg_received
        / max(avg_hours, 1.0)
        if avg_received > 0
        else 0.0
    )

    confidence_score = clamp(
        (
            min(total, 20)
            / 20
        )
        * 35
        + (
            min(
                observed_outcomes,
                10,
            )
            / 10
        )
        * 45
        + (
            20
            if confirmed > 0
            else 0
        )
    )

    payout_speed = 0.0

    received_with_dates = [
        item
        for item in paid_results
        if (
            item["received_at"]
            and item["execution_started_at"]
        )
    ]

    if received_with_dates:
        durations: list[float] = []

        for item in received_with_dates:
            try:
                started_time = (
                    datetime.fromisoformat(
                        str(
                            item[
                                "execution_started_at"
                            ]
                        ).replace(
                            "Z",
                            "+00:00",
                        )
                    )
                )

                received_time = (
                    datetime.fromisoformat(
                        str(
                            item["received_at"]
                        ).replace(
                            "Z",
                            "+00:00",
                        )
                    )
                )

                hours_to_payment = max(
                    (
                        received_time
                        - started_time
                    ).total_seconds()
                    / 3600,
                    0,
                )

                durations.append(
                    hours_to_payment
                )

            except ValueError:
                continue

        if durations:
            average_payment_hours = (
                sum(durations)
                / len(durations)
            )

            payout_speed = clamp(
                100
                / (
                    1
                    + average_payment_hours
                    / 24
                )
            )

    roi_score = clamp(
        conservative_rate
        * 45
        + min(
            math.log10(
                avg_roi + 1
            )
            * 15,
            35,
        )
        + payout_speed
        * 0.10
        + confidence_score
        * 0.10
    )

    connection.execute(
        """
        INSERT INTO source_reputation (
            source_name,
            total_opportunities,
            total_started,
            total_submitted,
            total_accepted,
            payment_confirmed,
            payment_failed,
            avg_reward,
            avg_received,
            avg_hours,
            payment_success_rate,
            conservative_success_rate,
            payout_speed,
            automation_success,
            confidence_score,
            roi_score,
            last_seen,
            updated_at
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?
        )
        ON CONFLICT(source_name) DO UPDATE SET
            total_opportunities =
                excluded.total_opportunities,
            total_started =
                excluded.total_started,
            total_submitted =
                excluded.total_submitted,
            total_accepted =
                excluded.total_accepted,
            payment_confirmed =
                excluded.payment_confirmed,
            payment_failed =
                excluded.payment_failed,
            avg_reward =
                excluded.avg_reward,
            avg_received =
                excluded.avg_received,
            avg_hours =
                excluded.avg_hours,
            payment_success_rate =
                excluded.payment_success_rate,
            conservative_success_rate =
                excluded.conservative_success_rate,
            payout_speed =
                excluded.payout_speed,
            automation_success =
                excluded.automation_success,
            confidence_score =
                excluded.confidence_score,
            roi_score =
                excluded.roi_score,
            last_seen =
                excluded.last_seen,
            updated_at =
                excluded.updated_at
        """,
        (
            source_name,
            total,
            started,
            submitted,
            accepted,
            confirmed,
            failed,
            avg_reward,
            avg_received,
            avg_hours,
            success_rate,
            conservative_rate,
            payout_speed,
            confidence_score,
            roi_score,
            now,
            now,
        ),
    )

    payment_methods = {
        str(
            item["settlement_target_key"]
            or item["settlement_provider"]
            or item["settlement_rail"]
            or "unknown"
        )
        for item in source_results
    }

    for payment_method in payment_methods:
        method_results = [
            item
            for item in source_results
            if str(
                item["settlement_target_key"]
                or item["settlement_provider"]
                or item["settlement_rail"]
                or "unknown"
            )
            == payment_method
        ]

        method_confirmed = sum(
            1
            for item in method_results
            if (
                str(
                    item["payment_status"]
                    or ""
                ).lower()
                == "received"
                and bool(
                    item["evidence_verified"]
                )
                and safe_float(
                    item["amount_received"]
                )
                > 0
            )
        )

        method_failed = sum(
            1
            for item in method_results
            if str(
                item["payment_status"]
                or ""
            ).lower()
            in {
                "failed",
                "rejected",
                "cancelled",
                "not_paid",
            }
        )

        method_observations = len(
            method_results
        )

        method_outcomes = (
            method_confirmed
            + method_failed
        )

        method_success = (
            method_confirmed
            / method_outcomes
            if method_outcomes > 0
            else 0.0
        )

        method_conservative = (
            wilson_lower_bound(
                method_confirmed,
                method_outcomes,
            )
            if method_outcomes > 0
            else 0.0
        )

        method_received = [
            safe_float(
                item["amount_received"]
            )
            for item in method_results
            if (
                str(
                    item["payment_status"]
                    or ""
                ).lower()
                == "received"
                and bool(
                    item["evidence_verified"]
                )
            )
        ]

        method_hours = [
            safe_float(
                item["execution_hours"]
            )
            for item in method_results
            if safe_float(
                item["execution_hours"]
            )
            > 0
        ]

        method_avg_received = (
            sum(method_received)
            / len(method_received)
            if method_received
            else 0.0
        )

        method_avg_hours = (
            sum(method_hours)
            / len(method_hours)
            if method_hours
            else 0.0
        )

        method_roi = (
            method_avg_received
            / max(
                method_avg_hours,
                1.0,
            )
            if method_avg_received > 0
            else 0.0
        )

        method_confidence = clamp(
            min(
                method_observations,
                20,
            )
            / 20
            * 50
            + min(
                method_outcomes,
                10,
            )
            / 10
            * 50
        )

        connection.execute(
            """
            INSERT INTO revenue_learning (
                source_name,
                payment_method,
                category,
                observations,
                successful_payments,
                failed_payments,
                success_rate,
                conservative_success_rate,
                avg_reward,
                avg_received,
                avg_hours,
                roi_score,
                confidence,
                updated_at
            )
            VALUES (
                ?, ?, 'paid_online_task', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            ON CONFLICT(
                source_name,
                payment_method,
                category
            ) DO UPDATE SET
                observations =
                    excluded.observations,
                successful_payments =
                    excluded.successful_payments,
                failed_payments =
                    excluded.failed_payments,
                success_rate =
                    excluded.success_rate,
                conservative_success_rate =
                    excluded.conservative_success_rate,
                avg_reward =
                    excluded.avg_reward,
                avg_received =
                    excluded.avg_received,
                avg_hours =
                    excluded.avg_hours,
                roi_score =
                    excluded.roi_score,
                confidence =
                    excluded.confidence,
                updated_at =
                    excluded.updated_at
            """,
            (
                source_name,
                payment_method,
                method_observations,
                method_confirmed,
                method_failed,
                method_success,
                method_conservative,
                avg_reward,
                method_avg_received,
                method_avg_hours,
                method_roi,
                method_confidence,
                now,
            ),
        )

    sources_updated += 1

connection.commit()

source_ranking = connection.execute(
    """
    SELECT *
    FROM source_reputation
    ORDER BY
        roi_score DESC,
        conservative_success_rate DESC,
        confidence_score DESC,
        avg_received DESC
    """
).fetchall()

learning_ranking = connection.execute(
    """
    SELECT *
    FROM revenue_learning
    ORDER BY
        roi_score DESC,
        conservative_success_rate DESC,
        confidence DESC
    """
).fetchall()

connection.execute(
    """
    UPDATE learning_runs
    SET
        finished_at = ?,
        results_analyzed = ?,
        sources_updated = ?,
        feedback_updated = ?,
        confirmed_payments = ?,
        confirmed_revenue = ?,
        status = 'success',
        notes = ?
    WHERE id = ?
    """,
    (
        utc_now(),
        len(results),
        sources_updated,
        feedback_updated,
        confirmed_payments,
        confirmed_revenue,
        (
            "Aprendizado calculado somente a partir "
            "de resultados e evidências registradas."
        ),
        run_id,
    ),
)

connection.commit()

report_lines = [
    "# Global Revenue Brain — Revenue Learning",
    "",
    f"Gerado em: {utc_now()}",
    "",
    "## Regra de verdade",
    "",
    (
        "Somente pagamentos recebidos com evidência verificada "
        "contam como sucesso financeiro."
    ),
    "",
    "## Resumo",
    "",
    f"- Resultados analisados: **{len(results)}**",
    f"- Fontes atualizadas: **{sources_updated}**",
    f"- Feedbacks atualizados: **{feedback_updated}**",
    f"- Pagamentos confirmados: **{confirmed_payments}**",
    f"- Receita confirmada aprendida: **{confirmed_revenue}**",
    "",
    "## Ranking das fontes",
    "",
]

for index, source in enumerate(
    source_ranking[:30],
    1,
):
    report_lines.extend([
        f"### {index}. {source['source_name']}",
        "",
        f"- Oportunidades: {source['total_opportunities']}",
        f"- Iniciadas: {source['total_started']}",
        f"- Submetidas: {source['total_submitted']}",
        f"- Aceitas: {source['total_accepted']}",
        f"- Pagamentos confirmados: {source['payment_confirmed']}",
        f"- Falhas de pagamento: {source['payment_failed']}",
        (
            "- Taxa observada de pagamento: "
            f"{round(source['payment_success_rate'] * 100, 2)}%"
        ),
        (
            "- Taxa conservadora: "
            f"{round(source['conservative_success_rate'] * 100, 2)}%"
        ),
        f"- Recompensa média anunciada: {source['avg_reward']}",
        f"- Valor médio recebido: {source['avg_received']}",
        f"- Horas médias: {source['avg_hours']}",
        f"- Confiança: {source['confidence_score']}",
        f"- ROI score: **{source['roi_score']}**",
        "",
    ])

report_lines.extend([
    "## Aprendizado por método de recebimento",
    "",
])

for index, learning in enumerate(
    learning_ranking[:30],
    1,
):
    report_lines.extend([
        (
            f"### {index}. "
            f"{learning['source_name']} / "
            f"{learning['payment_method']}"
        ),
        "",
        f"- Observações: {learning['observations']}",
        f"- Sucessos: {learning['successful_payments']}",
        f"- Falhas: {learning['failed_payments']}",
        (
            "- Taxa de sucesso: "
            f"{round(learning['success_rate'] * 100, 2)}%"
        ),
        (
            "- Taxa conservadora: "
            f"{round(learning['conservative_success_rate'] * 100, 2)}%"
        ),
        f"- Valor médio recebido: {learning['avg_received']}",
        f"- ROI: {learning['roi_score']}",
        f"- Confiança: {learning['confidence']}",
        "",
    ])

REPORT.write_text(
    "\n".join(report_lines),
    encoding="utf-8",
)

print()
print("===== REVENUE LEARNING SUMMARY =====")
print("Results analyzed:", len(results))
print("Sources updated:", sources_updated)
print("Feedback updated:", feedback_updated)
print("Confirmed payments:", confirmed_payments)
print("Confirmed revenue learned:", confirmed_revenue)

print()
print("===== SOURCE REPUTATION RANKING =====")

if source_ranking:
    for index, source in enumerate(
        source_ranking[:10],
        1,
    ):
        print()
        print(
            f"{index}. {source['source_name']}"
        )
        print(
            "   opportunities:",
            source["total_opportunities"],
        )
        print(
            "   confirmed payments:",
            source["payment_confirmed"],
        )
        print(
            "   observed success:",
            (
                f"{round(source['payment_success_rate'] * 100, 2)}%"
            ),
        )
        print(
            "   conservative success:",
            (
                f"{round(source['conservative_success_rate'] * 100, 2)}%"
            ),
        )
        print(
            "   average received:",
            source["avg_received"],
        )
        print(
            "   confidence:",
            source["confidence_score"],
        )
        print(
            "   ROI score:",
            source["roi_score"],
        )
else:
    print("Nenhuma fonte disponível.")

print()
print("===== LEARNING STATUS =====")

if confirmed_payments == 0:
    print(
        "Status: awaiting_confirmed_payment_evidence"
    )
    print(
        "Nenhum pagamento confirmado foi inventado."
    )
else:
    print(
        "Status: learning_from_confirmed_revenue"
    )

connection.close()


def run_downstream(
    script: Path,
    label: str,
) -> None:
    if not script.exists():
        print(
            f"{label}: skipped_missing_script"
        )
        return

    process = subprocess.run(
        [
            sys.executable,
            str(script),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=15 * 60,
        check=False,
    )

    print()
    print(
        f"===== {label} ====="
    )

    if process.stdout:
        print(
            process.stdout[-6000:]
        )

    if process.stderr:
        print(
            process.stderr[-3000:]
        )

    print(
        "Exit code:",
        process.returncode,
    )


run_downstream(
    PROBABILITY_CLASSIFIER,
    "RECLASSIFICATION AFTER LEARNING",
)

run_downstream(
    EXECUTION_RANKER,
    "RERANKING AFTER LEARNING",
)
