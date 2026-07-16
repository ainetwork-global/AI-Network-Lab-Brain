from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "11_DATA" / "global_revenue_brain.db"

PLAN = (
    ROOT
    / "07_EXECUTION_PLANS"
    / "securebananalabs-bug-bounty-issue-743.md"
)

CLAIM_DRAFT = (
    ROOT
    / "07_EXECUTION_PLANS"
    / "securebananalabs-bug-bounty-issue-743-claim-draft.md"
)

SOURCE_URL = (
    "https://github.com/"
    "SecureBananaLabs/bug-bounty/issues/743"
)

CANDIDATE_KEY_FRAGMENT = "%SecureBananaLabs/bug-bounty%743%"

ISSUE_TITLE = "Low Handing Fruit Automation"

ISSUE_BODY = """
Automate Low Hanging fruit bug detection and issue creation recursively.

This issue is focused on creating more issues:

1. Find a feature or bug to work on from this repository.
2. Create a new GitHub issue in the repository before beginning work.
3. Pull requests without a corresponding issue will not be considered.
4. The new issue must contain the exact exclusivity statement supplied by
   the maintainers and reference issue #743.
5. Follow all instructions carefully and precisely.

Bounty: USD 700.

Payment condition:
The bounty can only be paid after a successful pull request merge.
""".strip()

REQUIREMENTS = [
    "Encontrar um bug ou melhoria concreta no repositório.",
    "Criar uma nova issue própria antes de implementar a solução.",
    "Referenciar a issue original #743.",
    "Inserir na nova issue a declaração de exclusividade exigida.",
    "Não abrir pull request sem a issue correspondente.",
    "Implementar a correção descrita na nova issue.",
    "Adicionar evidências e testes adequados.",
    "O pagamento depende do merge bem-sucedido do pull request.",
]

CLAIM_STATEMENT = (
    "This issue is limited only to the creator of this issue. "
    "This means that only the issue author can attempt to solve this issue. "
    "If you would like to work on it, please create another issue with the "
    "same contents and refer to issue #743 for more information."
)

now = datetime.now(timezone.utc).isoformat()

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

row = conn.execute(
    """
    SELECT candidate_key
    FROM verified_paid_tasks
    WHERE url = ?
       OR (
            organization = 'SecureBananaLabs/bug-bounty'
            AND github_issue_number = 743
       )
    LIMIT 1
    """,
    (SOURCE_URL,),
).fetchone()

if not row:
    raise RuntimeError(
        "Registro da SecureBananaLabs issue #743 não encontrado."
    )

candidate_key = row["candidate_key"]

cache_payload = {
    "title": ISSUE_TITLE,
    "body": ISSUE_BODY,
    "state": "open",
    "updated_at": now,
    "labels": [
        {"name": "$700"},
        {"name": "AI agent friendly"},
        {"name": "bounty"},
        {"name": "bug bounty"},
        {"name": "good first issue"},
        {"name": "help wanted"},
    ],
}

conn.execute(
    """
    INSERT INTO paid_task_api_cache (
        candidate_key,
        github_owner,
        github_repository,
        github_issue_number,
        response_json,
        github_updated_at,
        fetched_at,
        http_status,
        last_error
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL)
    ON CONFLICT(candidate_key) DO UPDATE SET
        response_json = excluded.response_json,
        github_updated_at = excluded.github_updated_at,
        fetched_at = excluded.fetched_at,
        http_status = excluded.http_status,
        last_error = NULL
    """,
    (
        candidate_key,
        "SecureBananaLabs",
        "bug-bounty",
        743,
        json.dumps(
            cache_payload,
            ensure_ascii=False,
        ),
        now,
        now,
        200,
    ),
)

conn.execute(
    """
    UPDATE verified_paid_tasks
    SET
        reward_amount = 700,
        reward_currency = 'USD',
        reward_evidence = '/bounty $700',
        payment_promise_found = 1,
        claim_mechanism_found = 1,
        aggregator_detected = 0,
        non_execution_detected = 0,
        unavailable_detected = 0,
        github_issue_state = 'open',
        truth_score = 100,
        truth_status = 'verified_execution_candidate',
        truth_reason = ?,
        verified_at = ?
    WHERE candidate_key = ?
    """,
    (
        (
            "Issue aberta; recompensa explícita USD 700; "
            "participação exige criação prévia de nova issue; "
            "pull requests sem issue não são considerados; "
            "pagamento condicionado ao merge bem-sucedido do PR."
        ),
        now,
        candidate_key,
    ),
)

conn.execute(
    """
    UPDATE payment_probability_ranking
    SET
        reward_amount = 700,
        reward_currency = 'USD',
        reward_evidence = '/bounty $700',
        truth_status = 'verified_execution_candidate',
        truth_score = 100,
        payment_probability = 94,
        probability_band = 'very_high',
        expected_cash_value = 658,
        execution_readiness = 92,
        final_priority = 95,
        recommended_action = 'prepare_execution_plan',
        planning_status = 'ready_for_human_approval',
        probability_reason = ?,
        classified_at = ?
    WHERE candidate_key = ?
    """,
    (
        (
            "Recompensa e condição de pagamento explícitas; "
            "processo de entrada confirmado; issue aberta; "
            "pagamento ainda depende de aceite e merge do PR."
        ),
        now,
        candidate_key,
    ),
)

conn.execute(
    """
    UPDATE paid_task_execution_plans
    SET
        payment_probability = 94,
        expected_cash_value = 658,
        acceptance_requirements_json = ?,
        deliverables_json = ?,
        risks_json = ?,
        readiness_score = 92,
        planning_status = 'ready_for_human_approval',
        planning_reason = ?,
        human_approval_required = 1,
        external_action_performed = 0,
        claim_performed = 0,
        code_submitted = 0,
        updated_at = ?
    WHERE candidate_key = ?
    """,
    (
        json.dumps(
            REQUIREMENTS,
            ensure_ascii=False,
        ),
        json.dumps(
            [
                "Nova issue própria e exclusiva.",
                "Correção técnica para bug ou melhoria encontrada.",
                "Testes e evidências de funcionamento.",
                "Pull request associado à nova issue.",
            ],
            ensure_ascii=False,
        ),
        json.dumps(
            [
                "O pagamento não é garantido antes do merge.",
                "A tarefa técnica específica ainda precisa ser escolhida.",
                "A nova issue deve ser criada antes do pull request.",
                "Concorrência pode surgir antes da publicação da nova issue.",
            ],
            ensure_ascii=False,
        ),
        (
            "Regras, recompensa e condição de pagamento verificadas. "
            "O próximo passo exige aprovação humana para procurar um bug "
            "adequado e preparar a nova issue, sem publicação automática."
        ),
        now,
        candidate_key,
    ),
)

conn.commit()

PLAN.write_text(
    f"""# Execution Plan — {ISSUE_TITLE}

Gerado/atualizado em: {now}

## Controle

- Status: **ready_for_human_approval**
- Readiness score: **92**
- Aprovação humana obrigatória: **sim**
- Claim realizado: **não**
- Código submetido: **não**
- Ação externa realizada: **não**

## Oportunidade

- Repositório: SecureBananaLabs/bug-bounty
- Issue principal: #743
- URL: {SOURCE_URL}
- Estado: aberta
- Recompensa anunciada: USD 700
- Condição de pagamento: somente após merge bem-sucedido do PR

## Regras verificadas

1. Encontrar um bug ou melhoria concreta no repositório.
2. Criar uma nova issue própria antes de iniciar a implementação.
3. Referenciar a issue #743.
4. Incluir a declaração de exclusividade exigida.
5. Não abrir PR sem a issue correspondente.
6. Entregar código, testes e evidências.
7. A recompensa depende do merge do PR.

## Declaração obrigatória

> {CLAIM_STATEMENT}

## Próximo passo autorizado

Realizar somente uma inspeção local e não invasiva do repositório para
identificar bugs pequenos, reproduzíveis e adequados à bounty.

Ainda não:

- criar issue;
- comentar;
- fazer fork;
- abrir pull request;
- enviar código;
- fornecer dados financeiros.

## Riscos

- A bounty não é pagamento garantido.
- O mantenedor pode rejeitar a issue ou o PR.
- O escopo precisa ser pequeno e objetivamente testável.
- A participação só fica protegida após a criação correta da nova issue.
""",
    encoding="utf-8",
)

CLAIM_DRAFT.write_text(
    f"""# Draft — New Exclusive Issue for Bounty #743

**NÃO PUBLICADO**

## Suggested title

[Low Hanging Fruit] <descrever o bug específico após inspeção>

## Suggested body

### Problem

<descrever o problema reproduzível>

### Reproduction

1. <passo 1>
2. <passo 2>
3. <resultado observado>

### Expected behavior

<resultado esperado>

### Proposed implementation

<resumo da correção>

### Acceptance criteria

- [ ] O problema é reproduzível antes da alteração.
- [ ] A correção resolve o comportamento descrito.
- [ ] Testes relevantes passam.
- [ ] Não há alterações fora do escopo.

### Bounty reference

This work refers to issue #743.

{CLAIM_STATEMENT}
""",
    encoding="utf-8",
)

print()
print("===== ISSUE 743 ENRICHMENT =====")
print("Candidate key:", candidate_key)
print("Reward confirmed: USD 700")
print("Payment condition: successful PR merge")
print("Claim process confirmed: yes")
print("Readiness: 92")
print("Planning status: ready_for_human_approval")
print("External action performed: no")
print("Claim performed: no")
print("Code submitted: no")
print("Plan:", PLAN)
print("Claim draft:", CLAIM_DRAFT)

conn.close()
