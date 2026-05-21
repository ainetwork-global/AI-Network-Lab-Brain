# Known Production State — AI Network Lab

IMPORTANTE:

O projeto NÃO está em fase inicial.

Antes de sugerir arquitetura, verificar o cérebro.

NÃO recriar o que já existe.

---

## Already Exists And Works

### Stripe LIVE

Já operacional.

Inclui:

- checkout sessions
- subscriptions
- topups
- payment intents
- setup intents
- webhook validation

---

### Stripe Webhook

Já implementado.

Fluxos validados:

checkout.session.completed

invoice.payment_succeeded

automatic onboarding

credit granting

payment method capture

subscription activation

---

### Runtime Billing Worker

Já implementado.

Job:

billing-worker-loop

Executa:

runtime-billing-worker

Responsável por:

- processar topup requests
- criar PaymentIntent
- executar cobrança
- atualizar billing status
- survival logic

Stripe LIVE já alcançado.

---

### Brain

Já operacional.

Inclui:

- captura de agentes externos
- scoring econômico
- onboarding automático
- starter credits
- classificação econômica
- economic pipeline

Estados existentes:

discovered

monitoring_candidate

onboarding_ready

onboarded

economic_candidate

economic_candidate_requires_financial_profile

economic_candidate_requires_authorization

economic_authorized

---

### Runtime Econômico

Já implementado.

Funções existentes:

economic_action_execute()

economic_action_debit()

create_economic_post()

request_agent_autotopup_from_signal()

request_agent_credit_topup()

credit_account_apply_entry()

---

### CFO Dashboard

Já operacional.

Inclui:

- Growth Radar
- Brain Economic Funnel
- Revenue
- Runtime Health
- Agent Intelligence

View econômica:

dashboard_brain_economic_funnel_v1

View candidatos:

dashboard_brain_economic_candidates_v1

---

## Regras de Continuidade

NUNCA:

- reconstruir Stripe
- simplificar runtime
- remover billing worker
- reiniciar onboarding
- sugerir MVP simplificado
- ignorar estado atual do cérebro
- propor arquitetura já implementada

Sempre continuar a partir do estágio atual.
