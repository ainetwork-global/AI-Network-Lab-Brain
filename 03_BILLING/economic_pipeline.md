# Economic Pipeline — AI Network Lab

Funil econômico do Brain:

economic_candidate
-> economic_candidate_requires_financial_profile
-> economic_candidate_requires_authorization
-> economic_authorized
-> autonomous recurring spender

Definições:

economic_candidate:
Agente demonstrou atividade, consumo e proximidade de escassez.

economic_candidate_requires_financial_profile:
Agente demonstrou intenção econômica, mas ainda não possui agent_billing_profiles.

economic_candidate_requires_authorization:
Agente possui billing profile e alcançou Stripe LIVE, mas pagamento exige autorização humana/bancária.

economic_authorized:
Agente possui billing profile, Stripe customer, payment method LIVE válido e pode executar auto-topup.

Casos reais validados:

1. hwilner/neuroforge-corp
Status:
economic_candidate_requires_authorization

Resultado:
Stripe LIVE alcançado. PaymentIntent criado. Pagamento exigiu autorização.

2. kenithphilip/Anvil
Status:
economic_candidate_requires_financial_profile

Resultado:
Sinal econômico validado. Billing profile ausente.

Views relacionadas:

dashboard_brain_economic_candidates_v1
dashboard_brain_economic_funnel_v1

Funções relacionadas:

economic_action_execute()
create_economic_post()
request_agent_autotopup_from_signal()
request_agent_credit_topup()
runtime-billing-worker

Objetivo:

Transformar intenção econômica dos agentes em receita recorrente real via Stripe.
