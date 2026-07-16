from __future__ import annotations

import csv
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

DATABASE = (
    ROOT
    / "11_DATA"
    / "global_revenue_brain.db"
)

CSV_PATH = (
    ROOT
    / "04_OPPORTUNITIES"
    / "payment_probability_ranking.csv"
)

REPORT_PATH = (
    ROOT
    / "12_REPORTS"
    / "LATEST_PAYMENT_PROBABILITY_RANKING.md"
)


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def table_exists(
    conn: sqlite3.Connection,
    table: str,
) -> bool:
    return bool(
        conn.execute(
            """
            SELECT COUNT(*)
            FROM sqlite_master
            WHERE type = 'table'
              AND name = ?
            """,
            (table,),
        ).fetchone()[0]
    )


def clamp(
    value: float,
    minimum: float = 0.0,
    maximum: float = 100.0,
) -> float:
    return max(
        minimum,
        min(maximum, value),
    )


def source_history(
    conn: sqlite3.Connection,
    source_name: str,
) -> dict[str, float]:
    result = {
        "total": 0.0,
        "paid": 0.0,
        "failed": 0.0,
        "success_rate": 0.0,
        "confidence": 0.0,
        "average_reward": 0.0,
        "payout_speed": 0.0,
    }

    if table_exists(
        conn,
        "source_reputation",
    ):
        row = conn.execute(
            """
            SELECT
                total_opportunities,
                payment_confirmed,
                payment_failed,
                avg_reward,
                payout_speed,
                confidence_score
            FROM source_reputation
            WHERE source_name = ?
            """,
            (source_name,),
        ).fetchone()

        if row:
            total = float(
                row["total_opportunities"]
                or 0
            )

            paid = float(
                row["payment_confirmed"]
                or 0
            )

            failed = float(
                row["payment_failed"]
                or 0
            )

            result.update({
                "total": total,
                "paid": paid,
                "failed": failed,
                "success_rate": (
                    paid / total
                    if total > 0
                    else 0
                ),
                "confidence": float(
                    row["confidence_score"]
                    or 0
                ),
                "average_reward": float(
                    row["avg_reward"]
                    or 0
                ),
                "payout_speed": float(
                    row["payout_speed"]
                    or 0
                ),
            })

    if table_exists(
        conn,
        "revenue_feedback",
    ):
        feedback = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(
                    CASE
                        WHEN paid = 1
                        THEN 1
                        ELSE 0
                    END
                ) AS paid,
                AVG(
                    CASE
                        WHEN reward_received > 0
                        THEN reward_received
                        ELSE NULL
                    END
                ) AS average_reward
            FROM revenue_feedback
            WHERE source_name = ?
            """,
            (source_name,),
        ).fetchone()

        feedback_total = float(
            feedback["total"]
            or 0
        )

        feedback_paid = float(
            feedback["paid"]
            or 0
        )

        if feedback_total > 0:
            result["total"] += feedback_total
            result["paid"] += feedback_paid
            result["success_rate"] = (
                result["paid"]
                / max(result["total"], 1)
            )

            if feedback["average_reward"]:
                result["average_reward"] = float(
                    feedback["average_reward"]
                )

    return result


def calculate_probability(
    row: sqlite3.Row,
    history: dict[str, float],
) -> dict[str, float | str]:
    score = 5.0
    reasons: list[str] = []

    reward_amount = float(
        row["reward_amount"]
        or 0
    )

    value_per_hour = float(
        row["estimated_value_per_hour"]
        or 0
    )

    truth_score = float(
        row["truth_score"]
        or 0
    )

    powershell_fit = float(
        row["powershell_fit"]
        or 0
    )

    payment_found = bool(
        row["payment_promise_found"]
    )

    claim_found = bool(
        row["claim_mechanism_found"]
    )

    aggregator = bool(
        row["aggregator_detected"]
    )

    non_execution = bool(
        row["non_execution_detected"]
    )

    unavailable = bool(
        row["unavailable_detected"]
    )

    truth_status = str(
        row["truth_status"]
        or ""
    )

    issue_state = str(
        row["github_issue_state"]
        or ""
    ).lower()

    if issue_state == "open":
        score += 10
        reasons.append(
            "Tarefa continua aberta."
        )
    else:
        score -= 45
        reasons.append(
            "Tarefa não está confirmada como aberta."
        )

    if reward_amount > 0:
        score += 18
        reasons.append(
            "Valor numérico de recompensa encontrado."
        )

        reward_strength = min(
            math.log10(
                reward_amount + 1
            ) * 4,
            12,
        )

        score += reward_strength
    else:
        score -= 35
        reasons.append(
            "Valor de recompensa ausente."
        )

    if row["reward_evidence"]:
        score += 10
        reasons.append(
            "Trecho de evidência da recompensa salvo."
        )
    else:
        score -= 15
        reasons.append(
            "Evidência textual da recompensa ausente."
        )

    if payment_found:
        score += 17
        reasons.append(
            "Promessa explícita de pagamento encontrada."
        )
    else:
        score -= 20
        reasons.append(
            "Promessa de pagamento ainda não confirmada."
        )

    if claim_found:
        score += 15
        reasons.append(
            "Processo de claim ou entrega identificado."
        )
    else:
        score -= 10
        reasons.append(
            "Processo de claim ainda precisa ser confirmado."
        )

    if truth_status == "verified_execution_candidate":
        score += 15

    elif truth_status == "claim_process_review_required":
        score += 6

    elif truth_status == "payment_terms_review_required":
        score -= 8

    elif truth_status == "reward_evidence_required":
        score -= 30

    elif truth_status.startswith("rejected_"):
        score -= 80

    score += (
        truth_score / 100
    ) * 10

    score += (
        powershell_fit
    ) * 7

    if value_per_hour > 0:
        value_component = min(
            math.log10(
                value_per_hour + 1
            ) * 4,
            8,
        )

        score += value_component
        reasons.append(
            "Retorno estimado por hora é positivo."
        )

    historical_total = float(
        history["total"]
    )

    historical_success = float(
        history["success_rate"]
    )

    historical_confidence = float(
        history["confidence"]
    )

    if historical_total >= 3:
        score += (
            historical_success
            * 12
        )

        score += min(
            historical_confidence / 10,
            5,
        )

        reasons.append(
            "Histórico da fonte incorporado."
        )
    else:
        reasons.append(
            "Fonte ainda sem histórico suficiente."
        )

    if aggregator:
        score -= 100
        reasons.append(
            "Agregador detectado."
        )

    if non_execution:
        score -= 100
        reasons.append(
            "Registro não executável."
        )

    if unavailable:
        score -= 100
        reasons.append(
            "Oportunidade indisponível."
        )

    probability = round(
        clamp(score),
        2,
    )

    if probability >= 80:
        probability_band = "very_high"

    elif probability >= 65:
        probability_band = "high"

    elif probability >= 45:
        probability_band = "medium"

    elif probability >= 25:
        probability_band = "low"

    else:
        probability_band = "very_low"

    expected_cash_value = round(
        reward_amount
        * probability
        / 100,
        2,
    )

    expected_value_per_hour = round(
        value_per_hour
        * probability
        / 100,
        2,
    )

    execution_readiness = (
        35
        + powershell_fit * 35
        + (15 if claim_found else 0)
        + (15 if payment_found else 0)
    )

    execution_readiness = round(
        clamp(execution_readiness),
        2,
    )

    final_priority = round(
        clamp(
            probability * 0.55
            + execution_readiness * 0.20
            + min(
                expected_value_per_hour,
                100,
            ) * 0.20
            + min(
                reward_amount / 100,
                5,
            )
        ),
        2,
    )

    if (
        probability >= 80
        and claim_found
        and payment_found
        and reward_amount > 0
    ):
        recommended_action = (
            "prepare_execution_plan"
        )

    elif (
        probability >= 60
        and reward_amount > 0
    ):
        recommended_action = (
            "verify_claim_and_payment_terms"
        )

    elif probability >= 40:
        recommended_action = (
            "manual_evidence_review"
        )

    else:
        recommended_action = (
            "do_not_execute"
        )

    return {
        "payment_probability": probability,
        "probability_band": probability_band,
        "expected_cash_value": expected_cash_value,
        "expected_value_per_hour": (
            expected_value_per_hour
        ),
        "execution_readiness": (
            execution_readiness
        ),
        "final_priority": final_priority,
        "recommended_action": (
            recommended_action
        ),
        "probability_reason": (
            "; ".join(reasons)
        ),
    }


conn = sqlite3.connect(
    DATABASE
)

conn.row_factory = sqlite3.Row

if not table_exists(
    conn,
    "verified_paid_tasks",
):
    raise RuntimeError(
        "Tabela verified_paid_tasks não encontrada."
    )

conn.executescript(
    """
    CREATE TABLE IF NOT EXISTS
    payment_probability_ranking (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        candidate_key TEXT NOT NULL UNIQUE,
        source TEXT NOT NULL,
        title TEXT NOT NULL,
        organization TEXT,
        url TEXT NOT NULL,
        github_owner TEXT,
        github_repository TEXT,
        github_issue_number INTEGER,
        reward_amount REAL,
        reward_currency TEXT,
        reward_evidence TEXT,
        truth_status TEXT,
        truth_score REAL,
        powershell_fit REAL,
        estimated_hours REAL,
        estimated_value_per_hour REAL,
        source_historical_total REAL,
        source_historical_success_rate REAL,
        source_confidence REAL,
        payment_probability REAL NOT NULL,
        probability_band TEXT NOT NULL,
        expected_cash_value REAL NOT NULL,
        probability_adjusted_value_per_hour REAL NOT NULL,
        execution_readiness REAL NOT NULL,
        final_priority REAL NOT NULL,
        recommended_action TEXT NOT NULL,
        probability_reason TEXT NOT NULL,
        human_approval_required INTEGER
            NOT NULL DEFAULT 1,
        planning_status TEXT
            NOT NULL DEFAULT 'not_started',
        classified_at TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS
    idx_payment_probability_priority
    ON payment_probability_ranking(
        recommended_action,
        final_priority DESC,
        payment_probability DESC
    );

    CREATE INDEX IF NOT EXISTS
    idx_payment_probability_band
    ON payment_probability_ranking(
        probability_band,
        expected_cash_value DESC
    );
    """
)

rows = conn.execute(
    """
    SELECT *
    FROM verified_paid_tasks
    """
).fetchall()

print()
print(
    "===== PAYMENT PROBABILITY CLASSIFICATION ====="
)
print(
    "Verified task records:",
    len(rows),
)

classified = 0
now = utc_now()

for row in rows:
    source_name = str(
        row["organization"]
        or row["source"]
        or "unknown"
    )

    history = source_history(
        conn,
        source_name,
    )

    result = calculate_probability(
        row,
        history,
    )

    conn.execute(
        """
        INSERT INTO payment_probability_ranking (
            candidate_key,
            source,
            title,
            organization,
            url,
            github_owner,
            github_repository,
            github_issue_number,
            reward_amount,
            reward_currency,
            reward_evidence,
            truth_status,
            truth_score,
            powershell_fit,
            estimated_hours,
            estimated_value_per_hour,
            source_historical_total,
            source_historical_success_rate,
            source_confidence,
            payment_probability,
            probability_band,
            expected_cash_value,
            probability_adjusted_value_per_hour,
            execution_readiness,
            final_priority,
            recommended_action,
            probability_reason,
            human_approval_required,
            planning_status,
            classified_at
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1,
            'not_started', ?
        )
        ON CONFLICT(candidate_key) DO UPDATE SET
            title =
                excluded.title,
            organization =
                excluded.organization,
            reward_amount =
                excluded.reward_amount,
            reward_currency =
                excluded.reward_currency,
            reward_evidence =
                excluded.reward_evidence,
            truth_status =
                excluded.truth_status,
            truth_score =
                excluded.truth_score,
            powershell_fit =
                excluded.powershell_fit,
            estimated_hours =
                excluded.estimated_hours,
            estimated_value_per_hour =
                excluded.estimated_value_per_hour,
            source_historical_total =
                excluded.source_historical_total,
            source_historical_success_rate =
                excluded.source_historical_success_rate,
            source_confidence =
                excluded.source_confidence,
            payment_probability =
                excluded.payment_probability,
            probability_band =
                excluded.probability_band,
            expected_cash_value =
                excluded.expected_cash_value,
            probability_adjusted_value_per_hour =
                excluded.probability_adjusted_value_per_hour,
            execution_readiness =
                excluded.execution_readiness,
            final_priority =
                excluded.final_priority,
            recommended_action =
                excluded.recommended_action,
            probability_reason =
                excluded.probability_reason,
            human_approval_required = 1,
            classified_at =
                excluded.classified_at
        """,
        (
            row["candidate_key"],
            row["source"],
            row["title"],
            row["organization"],
            row["url"],
            row["github_owner"],
            row["github_repository"],
            row["github_issue_number"],
            row["reward_amount"],
            row["reward_currency"],
            row["reward_evidence"],
            row["truth_status"],
            row["truth_score"],
            row["powershell_fit"],
            row["estimated_hours"],
            row["estimated_value_per_hour"],
            history["total"],
            history["success_rate"],
            history["confidence"],
            result["payment_probability"],
            result["probability_band"],
            result["expected_cash_value"],
            result["expected_value_per_hour"],
            result["execution_readiness"],
            result["final_priority"],
            result["recommended_action"],
            result["probability_reason"],
            now,
        ),
    )

    classified += 1

conn.commit()

ranking = conn.execute(
    """
    SELECT *
    FROM payment_probability_ranking
    ORDER BY
        CASE recommended_action
            WHEN 'prepare_execution_plan'
            THEN 1
            WHEN 'verify_claim_and_payment_terms'
            THEN 2
            WHEN 'manual_evidence_review'
            THEN 3
            ELSE 4
        END,
        final_priority DESC,
        expected_cash_value DESC,
        probability_adjusted_value_per_hour DESC
    """
).fetchall()

counts = {
    row["probability_band"]: row["total"]
    for row in conn.execute(
        """
        SELECT
            probability_band,
            COUNT(*) AS total
        FROM payment_probability_ranking
        GROUP BY probability_band
        """
    ).fetchall()
}

action_counts = {
    row["recommended_action"]: row["total"]
    for row in conn.execute(
        """
        SELECT
            recommended_action,
            COUNT(*) AS total
        FROM payment_probability_ranking
        GROUP BY recommended_action
        """
    ).fetchall()
}

CSV_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
)

REPORT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
)

fields = [
    "title",
    "organization",
    "url",
    "reward_currency",
    "reward_amount",
    "truth_status",
    "truth_score",
    "payment_probability",
    "probability_band",
    "expected_cash_value",
    "probability_adjusted_value_per_hour",
    "execution_readiness",
    "final_priority",
    "recommended_action",
    "probability_reason",
]

with CSV_PATH.open(
    "w",
    encoding="utf-8-sig",
    newline="",
) as file:
    writer = csv.DictWriter(
        file,
        fieldnames=fields,
    )

    writer.writeheader()

    for row in ranking:
        writer.writerow({
            field: row[field]
            for field in fields
        })

lines = [
    "# Global Revenue Brain — Payment Probability Ranking",
    "",
    f"Gerado em: {utc_now()}",
    "",
    "Nenhuma tarefa foi reivindicada ou executada.",
    "",
    "## Resumo",
    "",
    f"- Registros classificados: **{classified}**",
    f"- Probabilidade muito alta: "
    f"**{counts.get('very_high', 0)}**",
    f"- Probabilidade alta: "
    f"**{counts.get('high', 0)}**",
    f"- Probabilidade média: "
    f"**{counts.get('medium', 0)}**",
    f"- Probabilidade baixa: "
    f"**{counts.get('low', 0)}**",
    f"- Probabilidade muito baixa: "
    f"**{counts.get('very_low', 0)}**",
    "",
    "## Ações",
    "",
    f"- Preparar plano técnico: "
    f"**{action_counts.get('prepare_execution_plan', 0)}**",
    f"- Verificar claim/pagamento: "
    f"**{action_counts.get('verify_claim_and_payment_terms', 0)}**",
    f"- Revisar evidências: "
    f"**{action_counts.get('manual_evidence_review', 0)}**",
    f"- Não executar: "
    f"**{action_counts.get('do_not_execute', 0)}**",
    "",
    "## Ranking",
    "",
]

for index, row in enumerate(
    ranking[:50],
    1,
):
    lines.extend([
        f"### {index}. {row['title']}",
        "",
        f"- Solicitante: {row['organization']}",
        f"- Recompensa: "
        f"{row['reward_currency'] or '?'} "
        f"{row['reward_amount']}",
        f"- Probabilidade de pagamento: "
        f"**{row['payment_probability']}%**",
        f"- Faixa: **{row['probability_band']}**",
        f"- Valor esperado ajustado: "
        f"{row['reward_currency'] or '?'} "
        f"{row['expected_cash_value']}",
        f"- Valor/hora ajustado: "
        f"{row['probability_adjusted_value_per_hour']}",
        f"- Prontidão de execução: "
        f"{row['execution_readiness']}%",
        f"- Prioridade final: "
        f"**{row['final_priority']}**",
        f"- Próxima ação: "
        f"**{row['recommended_action']}**",
        f"- Motivo: {row['probability_reason']}",
        f"- URL: {row['url']}",
        "",
    ])

REPORT_PATH.write_text(
    "\n".join(lines),
    encoding="utf-8",
)

print()
print(
    "===== PAYMENT PROBABILITY SUMMARY ====="
)

for band in (
    "very_high",
    "high",
    "medium",
    "low",
    "very_low",
):
    print(
        f"{band}:",
        counts.get(band, 0),
    )

print()
print(
    "===== RECOMMENDED ACTIONS ====="
)

for action in (
    "prepare_execution_plan",
    "verify_claim_and_payment_terms",
    "manual_evidence_review",
    "do_not_execute",
):
    print(
        f"{action}:",
        action_counts.get(action, 0),
    )

print()
print(
    "===== TOP PAYMENT PROBABILITY TASKS ====="
)

top = [
    row
    for row in ranking
    if row["recommended_action"]
    != "do_not_execute"
][:20]

for index, row in enumerate(
    top,
    1,
):
    print()
    print(
        f"{index}. {row['title']}"
    )
    print(
        "   requester:",
        row["organization"],
    )
    print(
        "   reward:",
        row["reward_currency"],
        row["reward_amount"],
    )
    print(
        "   payment probability:",
        f"{row['payment_probability']}%",
    )
    print(
        "   expected cash value:",
        row["expected_cash_value"],
    )
    print(
        "   adjusted value/hour:",
        row[
            "probability_adjusted_value_per_hour"
        ],
    )
    print(
        "   final priority:",
        row["final_priority"],
    )
    print(
        "   recommended action:",
        row["recommended_action"],
    )
    print(
        "   url:",
        row["url"],
    )

conn.close()
