from __future__ import annotations

import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

DATABASE = (
    ROOT
    / "11_DATA"
    / "global_revenue_brain.db"
)

INSPECTION_STATE = (
    ROOT
    / "00_CURRENT_STATE"
    / "SECUREBANANA_743_INSPECTION_STATE.json"
)

REPORT = (
    ROOT
    / "12_REPORTS"
    / "LATEST_ROI_DECISION.md"
)

CURRENT_DECISION = (
    ROOT
    / "00_CURRENT_STATE"
    / "CURRENT_ROI_DECISION.md"
)


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


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


if not INSPECTION_STATE.exists():
    raise RuntimeError(
        "Estado da inspeção local não encontrado: "
        f"{INSPECTION_STATE}"
    )

inspection = json.loads(
    INSPECTION_STATE.read_text(
        encoding="utf-8"
    )
)

connection = sqlite3.connect(
    DATABASE
)

connection.row_factory = sqlite3.Row

if not table_exists(
    connection,
    "execution_candidate_ranking",
):
    raise RuntimeError(
        "Tabela execution_candidate_ranking não encontrada."
    )

connection.executescript(
    """
    CREATE TABLE IF NOT EXISTS roi_decisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        candidate_key TEXT NOT NULL UNIQUE,
        title TEXT NOT NULL,
        organization TEXT,
        repository TEXT,
        issue_number INTEGER,
        source_url TEXT,

        reward_amount REAL NOT NULL DEFAULT 0,
        reward_currency TEXT,
        payment_probability REAL NOT NULL DEFAULT 0,
        expected_cash_value REAL NOT NULL DEFAULT 0,
        estimated_hours REAL NOT NULL DEFAULT 0,
        adjusted_value_per_hour REAL NOT NULL DEFAULT 0,

        ranking_score REAL NOT NULL DEFAULT 0,
        readiness_score REAL NOT NULL DEFAULT 0,
        execution_risk REAL NOT NULL DEFAULT 0,
        cash_speed REAL NOT NULL DEFAULT 0,

        files_analyzed INTEGER NOT NULL DEFAULT 0,
        test_files_found INTEGER NOT NULL DEFAULT 0,
        maintenance_signals INTEGER NOT NULL DEFAULT 0,
        candidate_files_found INTEGER NOT NULL DEFAULT 0,

        technical_feasibility REAL NOT NULL DEFAULT 0,
        evidence_strength REAL NOT NULL DEFAULT 0,
        financial_attractiveness REAL NOT NULL DEFAULT 0,
        time_efficiency REAL NOT NULL DEFAULT 0,
        inspection_quality REAL NOT NULL DEFAULT 0,

        roi_final_score REAL NOT NULL DEFAULT 0,
        decision TEXT NOT NULL,
        decision_reason TEXT NOT NULL,
        recommended_next_action TEXT NOT NULL,

        human_approval_required INTEGER
            NOT NULL DEFAULT 1,

        external_action_performed INTEGER
            NOT NULL DEFAULT 0,

        issue_created INTEGER
            NOT NULL DEFAULT 0,

        fork_created INTEGER
            NOT NULL DEFAULT 0,

        pull_request_created INTEGER
            NOT NULL DEFAULT 0,

        decided_at TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_roi_decisions_score
    ON roi_decisions(
        roi_final_score DESC,
        decision
    );
    """
)

ranking = connection.execute(
    """
    SELECT *
    FROM execution_candidate_ranking
    WHERE is_current_best_target = 1
    ORDER BY ranked_at DESC
    LIMIT 1
    """
).fetchone()

if not ranking:
    raise RuntimeError(
        "CURRENT_BEST_TARGET não encontrado."
    )

candidate_key = str(
    ranking["candidate_key"]
)

reward_amount = safe_float(
    ranking["reward_amount"]
)

payment_probability = safe_float(
    ranking["payment_probability"]
)

expected_cash_value = safe_float(
    ranking["expected_cash_value"]
)

estimated_hours = max(
    safe_float(
        ranking["estimated_hours"]
    ),
    1.0,
)

adjusted_value_per_hour = safe_float(
    ranking[
        "probability_adjusted_value_per_hour"
    ]
)

ranking_score = safe_float(
    ranking["final_execution_score"]
)

readiness_score = safe_float(
    ranking["readiness_score"]
)

execution_risk = safe_float(
    ranking["execution_risk"]
)

cash_speed = safe_float(
    ranking["cash_conversion_speed"]
)

files_analyzed = int(
    inspection.get(
        "files_analyzed",
        0,
    )
    or 0
)

test_files = inspection.get(
    "test_files",
    [],
) or []

signals = inspection.get(
    "signals",
    [],
) or []

candidate_files = inspection.get(
    "candidate_files",
    [],
) or []

languages = inspection.get(
    "languages",
    {},
) or {}

external_action = bool(
    inspection.get(
        "external_action_performed",
        False,
    )
)

issue_created = bool(
    inspection.get(
        "issue_created",
        False,
    )
)

fork_created = bool(
    inspection.get(
        "fork_created",
        False,
    )
)

pull_request_created = bool(
    inspection.get(
        "pull_request_created",
        False,
    )
)

technical_feasibility = 25.0

if files_analyzed > 0:
    technical_feasibility += 15

if languages:
    technical_feasibility += 10

if test_files:
    technical_feasibility += 20

if candidate_files:
    technical_feasibility += min(
        len(candidate_files) * 3,
        20,
    )

if readiness_score >= 80:
    technical_feasibility += 10

technical_feasibility = clamp(
    technical_feasibility
)

evidence_strength = clamp(
    payment_probability * 0.45
    + readiness_score * 0.25
    + ranking_score * 0.20
    + (
        10
        if reward_amount > 0
        else 0
    )
)

financial_attractiveness = clamp(
    payment_probability * 0.40
    + min(
        math.log10(
            expected_cash_value + 1
        ) * 18,
        35,
    )
    + min(
        math.log10(
            adjusted_value_per_hour + 1
        ) * 12,
        25,
    )
)

if estimated_hours <= 4:
    time_efficiency = 100.0

elif estimated_hours <= 8:
    time_efficiency = 80.0

elif estimated_hours <= 16:
    time_efficiency = 60.0

elif estimated_hours <= 40:
    time_efficiency = 35.0

else:
    time_efficiency = 15.0

inspection_quality = 0.0

if files_analyzed > 0:
    inspection_quality += 30

if languages:
    inspection_quality += 15

if test_files:
    inspection_quality += 20

if signals:
    inspection_quality += 10

if candidate_files:
    inspection_quality += 25

inspection_quality = clamp(
    inspection_quality
)

risk_penalty = (
    execution_risk * 0.22
)

if not test_files:
    risk_penalty += 7

if not candidate_files:
    risk_penalty += 12

if external_action:
    risk_penalty += 20

roi_final_score = clamp(
    financial_attractiveness * 0.30
    + evidence_strength * 0.20
    + technical_feasibility * 0.20
    + time_efficiency * 0.12
    + inspection_quality * 0.10
    + cash_speed * 0.08
    - risk_penalty
)

roi_final_score = round(
    roi_final_score,
    2,
)

reasons: list[str] = []

reasons.append(
    f"Probabilidade de pagamento: "
    f"{payment_probability}%."
)

reasons.append(
    f"Valor esperado: "
    f"{ranking['reward_currency']} "
    f"{expected_cash_value}."
)

reasons.append(
    f"Valor/hora ajustado: "
    f"{adjusted_value_per_hour}."
)

reasons.append(
    f"Arquivos analisados localmente: "
    f"{files_analyzed}."
)

reasons.append(
    f"Arquivos de teste encontrados: "
    f"{len(test_files)}."
)

reasons.append(
    f"Arquivos candidatos encontrados: "
    f"{len(candidate_files)}."
)

reasons.append(
    f"Risco de execução calculado: "
    f"{execution_risk}."
)

if (
    roi_final_score >= 75
    and candidate_files
    and payment_probability >= 75
    and not external_action
):
    decision = "EXECUTE_NOW"

    recommended_next_action = (
        "select_best_local_candidate_and_build_reproduction"
    )

    reasons.append(
        "A oportunidade passou pelos gates financeiro, "
        "técnico e operacional."
    )

elif (
    roi_final_score >= 55
    and files_analyzed > 0
    and not external_action
):
    decision = "INSPECT_DEEPER"

    recommended_next_action = (
        "inspect_top_candidate_files_and_find_reproducible_bug"
    )

    reasons.append(
        "A oportunidade é atraente, mas ainda falta "
        "um bug específico e reproduzível."
    )

elif roi_final_score >= 35:
    decision = "KEEP_IN_OBSERVATION"

    recommended_next_action = (
        "wait_for_better_evidence_or_new_candidate"
    )

    reasons.append(
        "O retorno potencial existe, mas os gates "
        "atuais ainda não justificam iniciar execução."
    )

else:
    decision = "REJECT"

    recommended_next_action = (
        "do_not_spend_execution_time"
    )

    reasons.append(
        "O retorno ajustado ao risco não é suficiente."
    )

decided_at = utc_now()

connection.execute(
    """
    INSERT INTO roi_decisions (
        candidate_key,
        title,
        organization,
        repository,
        issue_number,
        source_url,
        reward_amount,
        reward_currency,
        payment_probability,
        expected_cash_value,
        estimated_hours,
        adjusted_value_per_hour,
        ranking_score,
        readiness_score,
        execution_risk,
        cash_speed,
        files_analyzed,
        test_files_found,
        maintenance_signals,
        candidate_files_found,
        technical_feasibility,
        evidence_strength,
        financial_attractiveness,
        time_efficiency,
        inspection_quality,
        roi_final_score,
        decision,
        decision_reason,
        recommended_next_action,
        human_approval_required,
        external_action_performed,
        issue_created,
        fork_created,
        pull_request_created,
        decided_at
    )
    VALUES (
        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?
    )
    ON CONFLICT(candidate_key) DO UPDATE SET
        title =
            excluded.title,
        organization =
            excluded.organization,
        repository =
            excluded.repository,
        issue_number =
            excluded.issue_number,
        source_url =
            excluded.source_url,
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
        adjusted_value_per_hour =
            excluded.adjusted_value_per_hour,
        ranking_score =
            excluded.ranking_score,
        readiness_score =
            excluded.readiness_score,
        execution_risk =
            excluded.execution_risk,
        cash_speed =
            excluded.cash_speed,
        files_analyzed =
            excluded.files_analyzed,
        test_files_found =
            excluded.test_files_found,
        maintenance_signals =
            excluded.maintenance_signals,
        candidate_files_found =
            excluded.candidate_files_found,
        technical_feasibility =
            excluded.technical_feasibility,
        evidence_strength =
            excluded.evidence_strength,
        financial_attractiveness =
            excluded.financial_attractiveness,
        time_efficiency =
            excluded.time_efficiency,
        inspection_quality =
            excluded.inspection_quality,
        roi_final_score =
            excluded.roi_final_score,
        decision =
            excluded.decision,
        decision_reason =
            excluded.decision_reason,
        recommended_next_action =
            excluded.recommended_next_action,
        human_approval_required = 1,
        external_action_performed =
            excluded.external_action_performed,
        issue_created =
            excluded.issue_created,
        fork_created =
            excluded.fork_created,
        pull_request_created =
            excluded.pull_request_created,
        decided_at =
            excluded.decided_at
    """,
    (
        candidate_key,
        ranking["title"],
        ranking["organization"],
        ranking["repository"],
        ranking["issue_number"],
        ranking["source_url"],
        reward_amount,
        ranking["reward_currency"],
        payment_probability,
        expected_cash_value,
        estimated_hours,
        adjusted_value_per_hour,
        ranking_score,
        readiness_score,
        execution_risk,
        cash_speed,
        files_analyzed,
        len(test_files),
        len(signals),
        len(candidate_files),
        technical_feasibility,
        evidence_strength,
        financial_attractiveness,
        time_efficiency,
        inspection_quality,
        roi_final_score,
        decision,
        "; ".join(reasons),
        recommended_next_action,
        int(external_action),
        int(issue_created),
        int(fork_created),
        int(pull_request_created),
        decided_at,
    ),
)

connection.commit()

lines = [
    "# Global Revenue Brain — ROI Decision",
    "",
    f"Gerado em: {decided_at}",
    "",
    "## Decisão",
    "",
    f"# **{decision}**",
    "",
    f"- ROI final: **{roi_final_score}**",
    f"- Próxima ação: **{recommended_next_action}**",
    "- Aprovação humana obrigatória: **sim**",
    "- Ação externa realizada: **não**",
    "",
    "## Oportunidade",
    "",
    f"- Título: {ranking['title']}",
    f"- Solicitante: {ranking['organization']}",
    f"- Repositório: {ranking['repository']}",
    f"- Issue: #{ranking['issue_number']}",
    f"- Recompensa: "
    f"{ranking['reward_currency']} "
    f"{reward_amount}",
    f"- Probabilidade de pagamento: "
    f"{payment_probability}%",
    f"- Valor esperado: {expected_cash_value}",
    f"- Valor/hora ajustado: "
    f"{adjusted_value_per_hour}",
    f"- URL: {ranking['source_url']}",
    "",
    "## Componentes do ROI",
    "",
    f"- Atratividade financeira: "
    f"**{round(financial_attractiveness, 2)}**",
    f"- Força das evidências: "
    f"**{round(evidence_strength, 2)}**",
    f"- Viabilidade técnica: "
    f"**{round(technical_feasibility, 2)}**",
    f"- Eficiência de tempo: "
    f"**{round(time_efficiency, 2)}**",
    f"- Qualidade da inspeção: "
    f"**{round(inspection_quality, 2)}**",
    f"- Velocidade de caixa: "
    f"**{round(cash_speed, 2)}**",
    f"- Risco: **{round(execution_risk, 2)}**",
    "",
    "## Inspeção local",
    "",
    f"- Arquivos analisados: {files_analyzed}",
    f"- Testes encontrados: {len(test_files)}",
    f"- Marcadores de manutenção: {len(signals)}",
    f"- Arquivos candidatos: {len(candidate_files)}",
    "",
    "## Motivos",
    "",
]

lines.extend(
    f"- {reason}"
    for reason in reasons
)

lines.extend([
    "",
    "## Segurança operacional",
    "",
    "- Issue criada: não",
    "- Comentário publicado: não",
    "- Fork criado: não",
    "- Pull request criado: não",
    "- Código submetido: não",
])

REPORT.write_text(
    "\n".join(lines),
    encoding="utf-8",
)

CURRENT_DECISION.write_text(
    "\n".join(lines),
    encoding="utf-8",
)

print()
print("===== ROI DECISION ENGINE =====")
print("Title:", ranking["title"])
print(
    "Reward:",
    ranking["reward_currency"],
    reward_amount,
)
print(
    "Payment probability:",
    f"{payment_probability}%",
)
print(
    "Expected cash value:",
    expected_cash_value,
)
print(
    "Adjusted value/hour:",
    adjusted_value_per_hour,
)
print(
    "Files analyzed:",
    files_analyzed,
)
print(
    "Test files found:",
    len(test_files),
)
print(
    "Candidate files found:",
    len(candidate_files),
)

print()
print("===== ROI COMPONENTS =====")
print(
    "Financial attractiveness:",
    round(
        financial_attractiveness,
        2,
    ),
)
print(
    "Evidence strength:",
    round(
        evidence_strength,
        2,
    ),
)
print(
    "Technical feasibility:",
    round(
        technical_feasibility,
        2,
    ),
)
print(
    "Time efficiency:",
    round(
        time_efficiency,
        2,
    ),
)
print(
    "Inspection quality:",
    round(
        inspection_quality,
        2,
    ),
)
print(
    "Execution risk:",
    execution_risk,
)

print()
print("===== FINAL ROI DECISION =====")
print(
    "ROI final score:",
    roi_final_score,
)
print(
    "Decision:",
    decision,
)
print(
    "Recommended next action:",
    recommended_next_action,
)
print(
    "Human approval required: yes"
)
print(
    "External action performed: no"
)

connection.close()
