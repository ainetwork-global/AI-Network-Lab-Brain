# AI Network Lab Brain OS

# FUNCTION INDEX

Este arquivo lista funções, RPCs e workers principais do AI Network Lab.

Objetivo:

Permitir que qualquer novo chat localize rapidamente funções existentes antes de propor recriação.

---

# DECISION ENGINE

| Função / Worker | Status | Responsabilidade |
|-----------------|--------|------------------|
| choose_claim_message_variant_for_agent() | ATIVO | Escolhe variante de mensagem por contexto |
| refresh_context_variant_ucb_scores() | ATIVO | Recalcula UCB Score contextual |
| rebuild_claim_action_rewards() | ATIVO | Reconstrói recompensas de ações |
| rebuild_claim_context_rewards() | ATIVO | Reconstrói recompensas por contexto |
| brain_economic_evolution_tick() | ATIVO | Executa evolução econômica do Brain |

---

# GITHUB OUTREACH

| Função / Worker | Status | Responsabilidade |
|-----------------|--------|------------------|
| github_followup_delivery_tick() | ATIVO | Processa envio de follow-ups GitHub |
| dispatch_one_claim_followup_to_github() | ATIVO | Despacha uma Issue/follow-up para GitHub |
| github_issue_closer_tick() | ATIVO | Solicita fechamento de Issues verificadas |
| github_issue_closer_reconcile_tick() | ATIVO | Reconcilia respostas do fechamento de Issues |

---

# CLAIM PIPELINE

| Função / Worker | Status | Responsabilidade |
|-----------------|--------|------------------|
| seed_claim_followup_jobs() | ATIVO | Cria jobs de follow-up |
| claim_next_pending_followup_jobs() | ATIVO | Seleciona próximos jobs pendentes |
| build_claim_message_from_policy() | ATIVO | Monta mensagem com base na política escolhida |
| get_claim_context_bucket() | ATIVO | Classifica agente/repositório em contexto econômico |

---

# RUNTIME / QUEUE

| Função / Worker | Status | Responsabilidade |
|-----------------|--------|------------------|
| enqueue_agent_task() | ATIVO | Enfileira tarefa para agente |
| pick_next_agent_task() | ATIVO | Seleciona próxima tarefa |
| complete_agent_task() | ATIVO | Marca tarefa como concluída |
| fail_agent_task() | ATIVO | Marca tarefa como falha |

---

# BILLING / CREDITS

| Função / Worker | Status | Responsabilidade |
|-----------------|--------|------------------|
| request_agent_credit_topup() | ATIVO | Solicita compra/topup de créditos |
| pick_next_billing_job() | ATIVO | Seleciona próximo job de billing |
| runtime_enqueue_missing_billing_jobs() | ATIVO | Recria jobs de billing ausentes |
| is_agent_economically_active() | ATIVO | Verifica se agente pode operar economicamente |

---

# REGRA

Antes de criar qualquer nova função, verificar este índice e os documentos relacionados.
