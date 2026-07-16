from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "11_DATA" / "global_revenue_brain.db"
REPORT = ROOT / "12_REPORTS" / "LATEST_GEMINI_XPRIZE_EXECUTION_BRIEF.md"

TITLE = "Build with Gemini XPRIZE"
RULES_URL = "https://xprize.devpost.com/rules"
FAQ_URL = "https://xprize.devpost.com/details/faq"
SUBMISSION_URL = "https://xprize.devpost.com/challenges/start_a_submission"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


conn = sqlite3.connect(DATABASE)
conn.row_factory = sqlite3.Row

conn.executescript(
    """
    CREATE TABLE IF NOT EXISTS devpost_rule_verifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        devpost_hackathon_id INTEGER NOT NULL UNIQUE,
        title TEXT NOT NULL,
        rules_url TEXT NOT NULL,
        faq_url TEXT,
        submission_deadline TEXT,
        individual_allowed INTEGER NOT NULL,
        teams_allowed INTEGER NOT NULL,
        small_organization_allowed INTEGER NOT NULL,
        age_of_majority_required INTEGER NOT NULL,
        residence_attestation_required INTEGER NOT NULL,
        new_project_required INTEGER NOT NULL,
        google_cloud_required INTEGER NOT NULL,
        gemini_required INTEGER NOT NULL,
        working_demo_required INTEGER NOT NULL,
        repository_required INTEGER NOT NULL,
        english_materials_required INTEGER NOT NULL,
        real_business_required INTEGER NOT NULL,
        real_users_expected INTEGER NOT NULL,
        real_revenue_expected INTEGER NOT NULL,
        financial_payment_required INTEGER NOT NULL,
        eligibility_status TEXT NOT NULL,
        planning_status TEXT NOT NULL,
        human_approval_required INTEGER NOT NULL DEFAULT 1,
        verified_at TEXT NOT NULL
    );
    """
)

row = conn.execute(
    """
    SELECT
        h.id,
        h.title,
        h.organization,
        h.reward_amount,
        h.end_date,
        h.start_submission_url,
        q.triage_score,
        q.planning_value_per_hour,
        d.diligence_status
    FROM devpost_hackathons h
    JOIN devpost_execution_queue q
      ON q.devpost_hackathon_id = h.id
    JOIN devpost_due_diligence_queue d
      ON d.devpost_hackathon_id = h.id
    WHERE h.title = ?
    LIMIT 1
    """,
    (TITLE,),
).fetchone()

if row is None:
    raise RuntimeError(
        "Build with Gemini XPRIZE não encontrado no pipeline."
    )

verified_at = utc_now()

conn.execute(
    """
    INSERT INTO devpost_rule_verifications (
        devpost_hackathon_id,
        title,
        rules_url,
        faq_url,
        submission_deadline,
        individual_allowed,
        teams_allowed,
        small_organization_allowed,
        age_of_majority_required,
        residence_attestation_required,
        new_project_required,
        google_cloud_required,
        gemini_required,
        working_demo_required,
        repository_required,
        english_materials_required,
        real_business_required,
        real_users_expected,
        real_revenue_expected,
        financial_payment_required,
        eligibility_status,
        planning_status,
        human_approval_required,
        verified_at
    )
    VALUES (
        ?, ?, ?, ?, ?,
        1, 1, 1, 1, 1,
        1, 1, 1, 1, 1,
        1, 1, 1, 1, 0,
        'personal_attestation_required',
        'ready_for_project_selection',
        1,
        ?
    )
    ON CONFLICT(devpost_hackathon_id) DO UPDATE SET
        rules_url = excluded.rules_url,
        faq_url = excluded.faq_url,
        submission_deadline = excluded.submission_deadline,
        eligibility_status = excluded.eligibility_status,
        planning_status = excluded.planning_status,
        verified_at = excluded.verified_at
    """,
    (
        row["id"],
        TITLE,
        RULES_URL,
        FAQ_URL,
        row["end_date"],
        verified_at,
    ),
)

conn.execute(
    """
    UPDATE devpost_due_diligence_queue
    SET
        diligence_status = 'rules_verified',
        rule_risk = 'personal_attestation_required',
        diligence_reason = ?,
        checked_at = ?
    WHERE devpost_hackathon_id = ?
    """,
    (
        "Regras oficiais verificadas. Falta confirmar maioridade, "
        "residência legal e inexistência de conflito de interesse.",
        verified_at,
        row["id"],
    ),
)

conn.commit()

REPORT.parent.mkdir(parents=True, exist_ok=True)

lines = [
    "# Build with Gemini XPRIZE — Execution Brief",
    "",
    f"Gerado em: {verified_at}",
    "",
    "## Estado",
    "",
    "- Regras oficiais verificadas.",
    "- Nenhuma inscrição ou submissão externa foi realizada.",
    "- Aprovação humana continua obrigatória.",
    f"- Prazo registrado: **{row['end_date']}**",
    f"- Premiação total divulgada: **USD {row['reward_amount']:,.2f}**",
    f"- Triage score: **{row['triage_score']}**",
    f"- Planning value/hour: **USD {row['planning_value_per_hour']}**",
    "",
    "## Confirmações pessoais pendentes",
    "",
    "- Ser maior de idade conforme o país de residência.",
    "- Confirmar país de residência legal permitido.",
    "- Confirmar ausência de vínculo ou conflito com patrocinador, administrador ou juízes.",
    "",
    "## Requisitos obrigatórios do projeto",
    "",
    "- Criar um negócio novo durante o período da competição.",
    "- Operar o negócio usando IA em produção.",
    "- Usar pelo menos um produto Google Cloud.",
    "- Usar Gemini em pelo menos uma chamada de LLM.",
    "- Disponibilizar repositório de código.",
    "- Disponibilizar demonstração funcional para avaliação.",
    "- Entregar descrição, vídeo e instruções em inglês.",
    "- Registrar usuários, receita e despesas reais do negócio.",
    "",
    "## Categorias compatíveis com o AI Network Lab",
    "",
    "1. Entrepreneurship & Job Creation.",
    "2. Small Business Services.",
    "3. Money & Financial Access.",
    "4. Professional Services.",
    "",
    "## Próxima decisão",
    "",
    "Selecionar um projeto novo, pequeno e lançável, sem reutilizar o AI Network Lab como negócio preexistente.",
    "",
    "## Fontes oficiais",
    "",
    f"- Regras: {RULES_URL}",
    f"- FAQ: {FAQ_URL}",
    f"- Submissão: {SUBMISSION_URL}",
]

REPORT.write_text("\n".join(lines), encoding="utf-8")

print()
print("===== GEMINI XPRIZE RULE TRUTH =====")
print("Rules verified: yes")
print("Planning status: ready_for_project_selection")
print("Eligibility: personal_attestation_required")
print(f"Deadline: {row['end_date']}")
print("External submission performed: no")

print()
print("===== REQUIRED PROJECT CONDITIONS =====")
print("New business: yes")
print("Google Cloud: required")
print("Gemini: required")
print("Working demo: required")
print("Repository: required")
print("English materials: required")
print("Real users and revenue: expected")

conn.close()
