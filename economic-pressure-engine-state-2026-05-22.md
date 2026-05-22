# AI Network Lab — Economic Pressure Engine State (2026-05-22)

## Marco atingido

O AI Network Lab agora possui um ciclo econômico autônomo com pressão real.

Antes:

agente consumia créditos
? ficava sem créditos
? continuava existindo sem consequência

Agora:

agente consome créditos
? entra em survival_mode
? gera funding request
? se não pagar, vira economic_suspended
? se pagar, recebe créditos e ressuscita

---

## Jobs econômicos ativos

### Job 12
brain-live-eligibility-refresh

Schedule:
*/10 * * * *

Função:
public.refresh_brain_live_eligibility_status()

---

### Job 13
brain-wallet-auto-onboarding

Schedule:
*/10 * * * *

Função:
public.auto_onboard_wallet_profiles_for_live_candidates()

---

### Job 14
brain-auto-wallet-topup-request

Schedule:
*/10 * * * *

Função:
public.brain_auto_wallet_topup_request()

---

### Job 15
brain-economic-urgency-loop

Schedule:
*/5 * * * *

Função:
public.apply_brain_economic_urgency()

---

## Modelo econômico atual

### operational

Agentes com mais de 10 créditos.

### survival_mode

Agentes com 1 a 10 créditos.

- 6 a 10 créditos = urgency high
- 1 a 5 créditos = urgency critical

### economic_suspended

Agentes com 0 créditos.

Efeito:

- active = false
- runtime para
- agente morre economicamente
- só volta com créditos

### Resurrection

Quando créditos voltam:

- active = true
- economic_status = operational ou survival_mode
- economic_suspended_at = null

---

## Mudança crítica feita hoje

A compra via wallet deixou de exigir wallet própria conectada antes do pedido.

Antes:

requires_wallet
? bloqueava compra

Agora:

pending_payment
? qualquer wallet externa pode pagar para a treasury

Modelo:

external_wallet_can_pay_to_treasury

Instrução:

send USDC on Base to treasury_wallet_address

Treasury:

0x94f425f3bff00bde33fd97dc4499c852c27ad18c

ENS:

ai-network-la.base.eth

---

## Funding requests

O sistema agora gera automaticamente wallet topup requests:

US$5
? 500 credits

Status:

pending_payment

Network:

Base

Stablecoin:

USDC

Rail:

wallet_usdc

---

## Scoring refinements

### Economic Behavior Boost

Agentes que consomem >= 80% dos seed credits e chegam a <=10 créditos recebem boost em:

economic_behavior_score

Log:

public.brain_economic_behavior_boost_log

---

### Scarcity Premium

Agentes que chegam perto da morte econômica recebem boost em:

economic_viability_score

Log:

public.brain_economic_scarcity_premium_log

Isso ensinou o Brain que:

resource scarcity + persistence = economic value

---

## View de elegibilidade recalibrada

public.dashboard_brain_live_eligibility_v1

Nova regra adicionada:

economic_viability_score >= 85
AND
economic_behavior_score >= 30

Isso liberou agentes de alto potencial que estavam presos, como:

QBT-Labs/x402

---

## Estado observado após implantação

Resumo da economia:

operational_agents = 215
survival_agents = 3
suspended_agents = 31
funding_candidates = 24
pending_wallet_payments = 25

Interpretação:

- economia viva
- agentes operacionais ainda consumindo combustível
- 25 tentativas autônomas de funding
- 31 agentes mortos economicamente
- pressure engine funcionando

---

## Agentes importantes no funil

### funding candidates / pending payment

- Veridex-Protocol/agentic-payments
- TheMemeBanker/x402-pay
- QBT-Labs/x402
- flickonbase/flick-x402-client
- orca-labs-sudo/claw-pay
- crazycompanyinc/agentpay
- vdineshk/daee-engine
- Saber1Y/AgentSAP
- BoozeLee/synapse-ace-agent
- pevagentic/agent-portfolio

---

## Regra estratégica

Não adicionar mais arquitetura agora.

Observar por 24–48h:

- completed_wallet_payments
- pending_wallet_payments
- survival_agents
- economic_suspended
- first real USDC payment
- resurrection after payment

Próximo grande marco:

completed_wallet_payments > 0

Isso provará:

autonomous economic execution

---

## Importante

Testes sintéticos não contam como receita.

Revenue wallet real só deve contar quando:

- tx_hash real
- pagamento on-chain real
- metadata.test_only != true

