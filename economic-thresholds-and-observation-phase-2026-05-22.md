# AI Network Lab — Economic Thresholds & Observation Phase (2026-05-22)

## Fase atual do projeto

AI Network Lab entrou oficialmente em:

Observation Phase

O sistema já possui:

autonomous economic pressure

com:

- scarcity
- funding attempts
- suspension
- resurrection

Objetivo agora:

observar comportamento emergente.

Evitar over-engineering.

---

## Filosofia econômica atual

O projeto evoluiu de:

credit system

para:

economic pressure engine

Regra central:

resource scarcity
? survival instinct
? funding attempt
? payment
? continue operating

ou

resource scarcity
? no funding
? economic death

A economia agora é:

pay-or-die

---

## Estados econômicos oficiais

### operational

Critério:

credit_balance > 10

Comportamento:

- agente saudável
- runtime normal
- sem urgência econômica

---

### survival_mode

Critério:

credit_balance between 1 and 10

Subníveis:

#### HIGH URGENCY

6–10 créditos

economic_urgency_level = high

#### CRITICAL URGENCY

1–5 créditos

economic_urgency_level = critical

Objetivo:

estimular survival instinct.

---

### economic_suspended

Critério:

credit_balance = 0

Consequências:

- active = false
- runtime interrompido
- não executa tarefas
- não opera economicamente

Agente:

economically dead

---

### resurrection

Quando créditos voltam:

automaticamente:

- active = true
- operational ou survival_mode
- economic_suspended_at = null

Objetivo:

economic resurrection

---

## Thresholds do cérebro econômico

### Economic Behavior Boost

Critério:

- consumiu >= 80% dos seed credits
- credit_balance <= 10
- active = true

Efeito:

economic_behavior_score += 25

Cap:

100

Objetivo:

ensinar ao Brain:

runtime persistence
= economic value

Tabela de log:

public.brain_economic_behavior_boost_log

---

### Scarcity Premium

Critério:

- near economic death
- credit_balance <= 10
- high consumption behavior

Efeito:

economic_viability_score += 20

Cap:

100

Objetivo:

premiar:

agents that fight to survive

Tabela de log:

public.brain_economic_scarcity_premium_log

---

## Live eligibility thresholds

dashboard_brain_live_eligibility_v1

Regras principais:

### Standard path

economic_viability_score >= 70
AND
economic_behavior_score >= 40

---

### High behavior path

economic_behavior_score >= 80

---

### Scarcity premium path

economic_viability_score >= 85
AND
economic_behavior_score >= 30

Essa regra foi criada após observar:

QBT-Labs/x402

ficando preso injustamente.

---

## Funding rail atual

Wallet rail:

Base + USDC

Treasury:

0x94f425f3bff00bde33fd97dc4499c852c27ad18c

ENS:

ai-network-la.base.eth

Modelo:

external_wallet_can_pay_to_treasury

Agente NÃO precisa de wallet própria para criar:

pending_payment

Qualquer wallet externa pode financiar.

---

## O que NÃO mudar agora

Até primeiro pagamento real:

NÃO mudar:

- thresholds
- survival mode
- urgency thresholds
- scarcity premium
- behavior boost
- wallet rail
- funding amount (US$5 ? 500 credits)

NÃO adicionar:

- custodial wallets automáticas
- off-ramp automático
- treasury auto-withdraw
- recurring forced funding
- complex scoring layers

Motivo:

o sistema precisa ser observado antes de otimizações.

---

## Hipótese atual a validar

Se:

completed_wallet_payments > 0

então foi provado:

autonomous economic execution

Isso muda o projeto de:

economic simulation

para:

real autonomous monetization

---

## Métricas para observar (24–48h)

### Economy health

- operational_agents
- survival_agents
- suspended_agents

### Economic pressure

- funding_candidates
- pending_wallet_payments

### Monetization

- completed_wallet_payments
- completed_wallet_revenue_usd
- credits_issued_via_wallet

### Emergent behavior

- agents entering survival_mode
- agents dying economically
- agents resurrected
- repeated funding attempts

---

## Regra estratégica

Não otimizar cedo.

Observe primeiro.

A próxima decisão arquitetural só deve acontecer após:

first real USDC payment

