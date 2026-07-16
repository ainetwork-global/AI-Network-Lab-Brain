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
    / "execution_candidate_ranking.csv"
)

REPORT_PATH = (
    ROOT
    / "12_REPORTS"
    / "LATEST_EXECUTION_CANDIDATE_RANKING.md"
)

CURRENT_TARGET_PATH = (
    ROOT
    / "00_CURRENT_STATE"
    / "CURRENT_BEST_TARGET.md"
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


def calculate_cash_speed(
    *,
    claim_found: bool,
    payment_found: bool,
    planning_status: str,
    estimated_hours: float,
) -> float:
    score = 10.0

    if claim_found:
        score += 25

    if payment_found:
        score += 20

    if planning_status == "ready_for_human_approval":
        score += 25

    elif planning_status == "requirements_review_required":
        score += 12

    if estimated_hours <= 4:
        score += 20

    elif estimated_hours <= 8:
        score += 14

    elif estimated_hours <= 16:
        score += 7

    return round(
        clamp(score),
        2,
    )


def calculate_risk(
    *,
    truth_status: str,
    planning_status: str,
    claim_found: bool,
    payment_found: bool,
    source_history_total: float,
) -> float:
    risk = 35.0

    if truth_status == "verified_execution_candidate":
        risk -= 18

    elif truth_status == "claim_process_review_required":
        risk -= 5

    elif truth_status == "payment_terms_review_required":
        risk += 15

    elif truth_status.startswith("rejected_"):
        risk += 100

    if planning_status == "ready_for_human_approval":
        risk -= 12

    elif planning_status == "requirements_review_required":
        risk += 8

    elif planning_status in {
        "not_ready",
        "blocked_safety_review",
    }:
        risk += 60

    if not claim_found:
        risk += 12

    if not payment_found:
        risk += 18

    if source_history_total <= 0:
        risk += 8

    return round(
        clamp(risk),
        2,
    )


conn = sqlite3.connect(
    DATABASE
)

conn.row_factory = sqlite3.Row

required_tables = (
    "payment_probability_ranking",
    "verified_paid_tasks",
)

for table in required_tables:
    if not table_exists(
        conn,
        table,
    ):
        raise RuntimeError(
            f"Tabela obrigatória ausente: {table}"
        )

has_plans = table_exists(
    conn,
    "paid_task_execution_plans",
)

conn.executescript(
    """
    CREATE TABLE IF NOT EXISTS
    execution_candidate_ranking (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        candidate_key TEXT NOT NULL UNIQUE,
        rank_position INTEGER,
        is_current_best_target INTEGER
            NOT NULL DEFAULT 0,
        title TEXT NOT NULL,
        organization TEXT,
        source_url TEXT NOT NULL,
        repository TEXT,
        issue_number INTEGER,
        reward_amount REAL,
        reward_currency TEXT,
        payment_probability REAL,
        expected_cash_value REAL,
        estimated_hours REAL,
        probability_adjusted_value_per_hour REAL,
        truth_status TEXT,
        truth_score REAL,
        claim_mechanism_found INTEGER
            NOT NULL DEFAULT 0,
        payment_promise_found INTEGER
            NOT NULL DEFAULT 0,
        planning_status TEXT,
        readiness_score REAL,
        source_history_total REAL,
        source_success_rate REAL,
        cash_conversion_speed REAL,
        execution_risk REAL,
        opportunity_value_score REAL,
        execution_efficiency_score REAL,
        final_execution_score REAL,
        recommended_action TEXT,
        human_approval_required INTEGER
            NOT NULL DEFAULT 1,
        external_action_performed INTEGER
            NOT NULL DEFAULT 0,
        ranked_at TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS
    idx_execution_candidate_rank
    ON execution_candidate_ranking(
        is_current_best_target DESC,
        rank_position ASC,
        final_execution_score DESC
    );
    """
)

if has_plans:
    query = """
        SELECT
            p.candidate_key,
            p.title,
            p.organization,
            p.url AS source_url,
            p.github_owner,
            p.github_repository,
            p.github_issue_number,
            p.reward_amount,
            p.reward_currency,
            p.payment_probability,
            p.expected_cash_value,
            p.estimated_hours,
            p.probability_adjusted_value_per_hour,
            p.truth_status,
            p.truth_score,
            p.source_historical_total,
            p.source_historical_success_rate,
            p.recommended_action,
            v.claim_mechanism_found,
            v.payment_promise_found,
            COALESCE(
                e.planning_status,
                p.planning_status,
                'not_started'
            ) AS planning_status,
            COALESCE(
                e.readiness_score,
                0
            ) AS readiness_score,
            COALESCE(
                e.repository,
                p.organization
            ) AS repository,
            COALESCE(
                e.issue_number,
                p.github_issue_number
            ) AS issue_number
        FROM payment_probability_ranking p
        JOIN verified_paid_tasks v
          ON v.candidate_key = p.candidate_key
        LEFT JOIN paid_task_execution_plans e
          ON e.candidate_key = p.candidate_key
        WHERE COALESCE(p.reward_amount, 0) > 0
          AND COALESCE(p.payment_probability, 0) >= 25
          AND p.truth_status NOT LIKE 'rejected_%'
          AND COALESCE(
              e.planning_status,
              p.planning_status,
              'not_started'
          ) != 'blocked_safety_review'
    """
else:
    query = """
        SELECT
            p.candidate_key,
            p.title,
            p.organization,
            p.url AS source_url,
            p.github_owner,
            p.github_repository,
            p.github_issue_number,
            p.reward_amount,
            p.reward_currency,
            p.payment_probability,
            p.expected_cash_value,
            p.estimated_hours,
            p.probability_adjusted_value_per_hour,
            p.truth_status,
            p.truth_score,
            p.source_historical_total,
            p.source_historical_success_rate,
            p.recommended_action,
            v.claim_mechanism_found,
            v.payment_promise_found,
            COALESCE(
                p.planning_status,
                'not_started'
            ) AS planning_status,
            0 AS readiness_score,
            p.organization AS repository,
            p.github_issue_number AS issue_number
        FROM payment_probability_ranking p
        JOIN verified_paid_tasks v
          ON v.candidate_key = p.candidate_key
        WHERE COALESCE(p.reward_amount, 0) > 0
          AND COALESCE(p.payment_probability, 0) >= 25
          AND p.truth_status NOT LIKE 'rejected_%'
    """

rows = conn.execute(
    query
).fetchall()

ranked_candidates = []

print()
print("===== EXECUTION CANDIDATE RANKING =====")
print("Candidates eligible:", len(rows))

for row in rows:
    reward_amount = float(
        row["reward_amount"]
        or 0
    )

    payment_probability = float(
        row["payment_probability"]
        or 0
    )

    expected_cash_value = float(
        row["expected_cash_value"]
        or 0
    )

    estimated_hours = max(
        float(
            row["estimated_hours"]
            or 0
        ),
        1.0,
    )

    adjusted_value_per_hour = float(
        row[
            "probability_adjusted_value_per_hour"
        ]
        or 0
    )

    truth_score = float(
        row["truth_score"]
        or 0
    )

    readiness_score = float(
        row["readiness_score"]
        or 0
    )

    source_history_total = float(
        row["source_historical_total"]
        or 0
    )

    source_success_rate = float(
        row["source_historical_success_rate"]
        or 0
    )

    claim_found = bool(
        row["claim_mechanism_found"]
    )

    payment_found = bool(
        row["payment_promise_found"]
    )

    planning_status = str(
        row["planning_status"]
        or "not_started"
    )

    truth_status = str(
        row["truth_status"]
        or ""
    )

    cash_speed = calculate_cash_speed(
        claim_found=claim_found,
        payment_found=payment_found,
        planning_status=planning_status,
        estimated_hours=estimated_hours,
    )

    execution_risk = calculate_risk(
        truth_status=truth_status,
        planning_status=planning_status,
        claim_found=claim_found,
        payment_found=payment_found,
        source_history_total=source_history_total,
    )

    opportunity_value_score = clamp(
        payment_probability * 0.45
        + truth_score * 0.15
        + min(
            math.log10(
                expected_cash_value + 1
            ) * 12,
            25,
        )
        + min(
            source_success_rate * 15,
            15,
        )
    )

    execution_efficiency_score = clamp(
        readiness_score * 0.35
        + cash_speed * 0.30
        + min(
            math.log10(
                adjusted_value_per_hour + 1
            ) * 14,
            25,
        )
        + (
            10
            if estimated_hours <= 8
            else 4
        )
    )

    final_execution_score = clamp(
        opportunity_value_score * 0.45
        + execution_efficiency_score * 0.35
        + payment_probability * 0.20
        - execution_risk * 0.25
    )

    final_execution_score = round(
        final_execution_score,
        2,
    )

    if (
        planning_status
        == "ready_for_human_approval"
        and final_execution_score >= 65
    ):
        recommended_action = (
            "request_human_approval_to_begin"
        )

    elif (
        planning_status
        == "requirements_review_required"
    ):
        recommended_action = (
            "complete_requirements_verification"
        )

    elif (
        payment_probability >= 60
    ):
        recommended_action = (
            "prepare_or_refresh_execution_plan"
        )

    else:
        recommended_action = (
            "keep_in_observation"
        )

    ranked_candidates.append({
        "candidate_key": row["candidate_key"],
        "title": row["title"],
        "organization": row["organization"],
        "source_url": row["source_url"],
        "repository": row["repository"],
        "issue_number": row["issue_number"],
        "reward_amount": reward_amount,
        "reward_currency": row["reward_currency"],
        "payment_probability": payment_probability,
        "expected_cash_value": expected_cash_value,
        "estimated_hours": estimated_hours,
        "probability_adjusted_value_per_hour":
            adjusted_value_per_hour,
        "truth_status": truth_status,
        "truth_score": truth_score,
        "claim_mechanism_found":
            int(claim_found),
        "payment_promise_found":
            int(payment_found),
        "planning_status": planning_status,
        "readiness_score": readiness_score,
        "source_history_total":
            source_history_total,
        "source_success_rate":
            source_success_rate,
        "cash_conversion_speed":
            cash_speed,
        "execution_risk":
            execution_risk,
        "opportunity_value_score": round(
            opportunity_value_score,
            2,
        ),
        "execution_efficiency_score": round(
            execution_efficiency_score,
            2,
        ),
        "final_execution_score":
            final_execution_score,
        "recommended_action":
            recommended_action,
    })

ranked_candidates.sort(
    key=lambda item: (
        item["final_execution_score"],
        item["expected_cash_value"],
        item[
            "probability_adjusted_value_per_hour"
        ],
    ),
    reverse=True,
)

conn.execute(
    """
    UPDATE execution_candidate_ranking
    SET
        is_current_best_target = 0,
        rank_position = NULL
    """
)

ranked_at = utc_now()

for position, item in enumerate(
    ranked_candidates,
    1,
):
    is_best = int(
        position == 1
    )

    conn.execute(
        """
        INSERT INTO execution_candidate_ranking (
            candidate_key,
            rank_position,
            is_current_best_target,
            title,
            organization,
            source_url,
            repository,
            issue_number,
            reward_amount,
            reward_currency,
            payment_probability,
            expected_cash_value,
            estimated_hours,
            probability_adjusted_value_per_hour,
            truth_status,
            truth_score,
            claim_mechanism_found,
            payment_promise_found,
            planning_status,
            readiness_score,
            source_history_total,
            source_success_rate,
            cash_conversion_speed,
            execution_risk,
            opportunity_value_score,
            execution_efficiency_score,
            final_execution_score,
            recommended_action,
            human_approval_required,
            external_action_performed,
            ranked_at
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0, ?
        )
        ON CONFLICT(candidate_key) DO UPDATE SET
            rank_position =
                excluded.rank_position,
            is_current_best_target =
                excluded.is_current_best_target,
            title =
                excluded.title,
            organization =
                excluded.organization,
            source_url =
                excluded.source_url,
            repository =
                excluded.repository,
            issue_number =
                excluded.issue_number,
            reward_amount =
                excluded.reward_amount,
            reward_currency =
                excluded.reward_currency,
            payment_probability =
                excluded.payment_probability,
            expected_cash_value =
                excluded.expected_cash_value,
            estimated_hours =
                excluded.estimated_hours,
            probability_adjusted_value_per_hour =
                excluded.probability_adjusted_value_per_hour,
            truth_status =
                excluded.truth_status,
            truth_score =
                excluded.truth_score,
            claim_mechanism_found =
                excluded.claim_mechanism_found,
            payment_promise_found =
                excluded.payment_promise_found,
            planning_status =
                excluded.planning_status,
            readiness_score =
                excluded.readiness_score,
            source_history_total =
                excluded.source_history_total,
            source_success_rate =
                excluded.source_success_rate,
            cash_conversion_speed =
                excluded.cash_conversion_speed,
            execution_risk =
                excluded.execution_risk,
            opportunity_value_score =
                excluded.opportunity_value_score,
            execution_efficiency_score =
                excluded.execution_efficiency_score,
            final_execution_score =
                excluded.final_execution_score,
            recommended_action =
                excluded.recommended_action,
            human_approval_required = 1,
            external_action_performed = 0,
            ranked_at =
                excluded.ranked_at
        """,
        (
            item["candidate_key"],
            position,
            is_best,
            item["title"],
            item["organization"],
            item["source_url"],
            item["repository"],
            item["issue_number"],
            item["reward_amount"],
            item["reward_currency"],
            item["payment_probability"],
            item["expected_cash_value"],
            item["estimated_hours"],
            item[
                "probability_adjusted_value_per_hour"
            ],
            item["truth_status"],
            item["truth_score"],
            item["claim_mechanism_found"],
            item["payment_promise_found"],
            item["planning_status"],
            item["readiness_score"],
            item["source_history_total"],
            item["source_success_rate"],
            item["cash_conversion_speed"],
            item["execution_risk"],
            item["opportunity_value_score"],
            item[
                "execution_efficiency_score"
            ],
            item["final_execution_score"],
            item["recommended_action"],
            ranked_at,
        ),
    )

conn.commit()

CSV_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
)

csv_fields = [
    "rank_position",
    "is_current_best_target",
    "title",
    "organization",
    "repository",
    "issue_number",
    "reward_currency",
    "reward_amount",
    "payment_probability",
    "expected_cash_value",
    "estimated_hours",
    "probability_adjusted_value_per_hour",
    "planning_status",
    "readiness_score",
    "cash_conversion_speed",
    "execution_risk",
    "final_execution_score",
    "recommended_action",
    "source_url",
]

with CSV_PATH.open(
    "w",
    encoding="utf-8-sig",
    newline="",
) as file:
    writer = csv.DictWriter(
        file,
        fieldnames=csv_fields,
    )

    writer.writeheader()

    for position, item in enumerate(
        ranked_candidates,
        1,
    ):
        writer.writerow({
            "rank_position": position,
            "is_current_best_target":
                int(position == 1),
            **{
                field: item[field]
                for field in csv_fields
                if field not in {
                    "rank_position",
                    "is_current_best_target",
                }
            },
        })

REPORT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
)

report_lines = [
    "# Global Revenue Brain — Execution Candidate Ranking",
    "",
    f"Gerado em: {ranked_at}",
    "",
    "Nenhuma ação externa foi realizada.",
    "",
    "## Resumo",
    "",
    f"- Candidatos elegíveis: "
    f"**{len(ranked_candidates)}**",
    f"- CURRENT_BEST_TARGET: "
    f"**{'definido' if ranked_candidates else 'não definido'}**",
    "",
]

if ranked_candidates:
    best = ranked_candidates[0]

    report_lines.extend([
        "## CURRENT_BEST_TARGET",
        "",
        f"### {best['title']}",
        "",
        f"- Solicitante: {best['organization']}",
        f"- Repositório: {best['repository']}",
        f"- Issue: #{best['issue_number']}",
        f"- Recompensa: "
        f"{best['reward_currency']} "
        f"{best['reward_amount']}",
        f"- Probabilidade de pagamento: "
        f"**{best['payment_probability']}%**",
        f"- Valor esperado: "
        f"{best['expected_cash_value']}",
        f"- Valor/hora ajustado: "
        f"{best['probability_adjusted_value_per_hour']}",
        f"- Readiness: "
        f"{best['readiness_score']}",
        f"- Velocidade de caixa: "
        f"{best['cash_conversion_speed']}",
        f"- Risco: "
        f"{best['execution_risk']}",
        f"- Score final: "
        f"**{best['final_execution_score']}**",
        f"- Próxima ação: "
        f"**{best['recommended_action']}**",
        f"- URL: {best['source_url']}",
        "",
        "## TOP 10",
        "",
    ])

    for position, item in enumerate(
        ranked_candidates[:10],
        1,
    ):
        report_lines.extend([
            f"### {position}. {item['title']}",
            "",
            f"- Recompensa: "
            f"{item['reward_currency']} "
            f"{item['reward_amount']}",
            f"- Probabilidade: "
            f"{item['payment_probability']}%",
            f"- Valor esperado: "
            f"{item['expected_cash_value']}",
            f"- Score final: "
            f"**{item['final_execution_score']}**",
            f"- Status do plano: "
            f"{item['planning_status']}",
            f"- Próxima ação: "
            f"{item['recommended_action']}",
            f"- URL: {item['source_url']}",
            "",
        ])

REPORT_PATH.write_text(
    "\n".join(report_lines),
    encoding="utf-8",
)

CURRENT_TARGET_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
)

if ranked_candidates:
    best = ranked_candidates[0]

    current_target_lines = [
        "# CURRENT BEST TARGET",
        "",
        f"Atualizado em: {ranked_at}",
        "",
        f"## {best['title']}",
        "",
        f"- Solicitante: {best['organization']}",
        f"- Repositório: {best['repository']}",
        f"- Issue: #{best['issue_number']}",
        f"- Recompensa: "
        f"{best['reward_currency']} "
        f"{best['reward_amount']}",
        f"- Probabilidade de pagamento: "
        f"{best['payment_probability']}%",
        f"- Valor esperado: "
        f"{best['expected_cash_value']}",
        f"- Valor/hora ajustado: "
        f"{best['probability_adjusted_value_per_hour']}",
        f"- Score final: "
        f"{best['final_execution_score']}",
        f"- Status do plano: "
        f"{best['planning_status']}",
        f"- Próxima ação: "
        f"**{best['recommended_action']}**",
        f"- URL: {best['source_url']}",
        "",
        "## Segurança operacional",
        "",
        "- Aprovação humana obrigatória: sim",
        "- Claim realizado: não",
        "- Código submetido: não",
        "- Ação externa realizada: não",
    ]
else:
    current_target_lines = [
        "# CURRENT BEST TARGET",
        "",
        f"Atualizado em: {ranked_at}",
        "",
        "Nenhuma oportunidade atingiu os gates mínimos.",
    ]

CURRENT_TARGET_PATH.write_text(
    "\n".join(current_target_lines),
    encoding="utf-8",
)

print()
print("===== EXECUTION RANKING SUMMARY =====")
print(
    "Eligible candidates:",
    len(ranked_candidates),
)

if ranked_candidates:
    best = ranked_candidates[0]

    print()
    print("===== CURRENT BEST TARGET =====")
    print("Title:", best["title"])
    print(
        "Requester:",
        best["organization"],
    )
    print(
        "Reward:",
        best["reward_currency"],
        best["reward_amount"],
    )
    print(
        "Payment probability:",
        f"{best['payment_probability']}%",
    )
    print(
        "Expected cash value:",
        best["expected_cash_value"],
    )
    print(
        "Adjusted value/hour:",
        best[
            "probability_adjusted_value_per_hour"
        ],
    )
    print(
        "Readiness:",
        best["readiness_score"],
    )
    print(
        "Cash speed:",
        best["cash_conversion_speed"],
    )
    print(
        "Execution risk:",
        best["execution_risk"],
    )
    print(
        "Final execution score:",
        best["final_execution_score"],
    )
    print(
        "Recommended action:",
        best["recommended_action"],
    )
    print(
        "URL:",
        best["source_url"],
    )
else:
    print(
        "CURRENT BEST TARGET: none"
    )

print()
print("===== TOP 10 EXECUTION CANDIDATES =====")

for position, item in enumerate(
    ranked_candidates[:10],
    1,
):
    print()
    print(
        f"{position}. {item['title']}"
    )
    print(
        "   reward:",
        item["reward_currency"],
        item["reward_amount"],
    )
    print(
        "   probability:",
        f"{item['payment_probability']}%",
    )
    print(
        "   expected cash:",
        item["expected_cash_value"],
    )
    print(
        "   final score:",
        item["final_execution_score"],
    )
    print(
        "   action:",
        item["recommended_action"],
    )

conn.close()
