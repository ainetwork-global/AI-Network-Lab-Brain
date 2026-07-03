# AI Network Lab Brain
## Migration Snapshot
### Date
2026-07-03
### File
AI-Network-Lab-Brain-State-2026-07-03-Revenue-Truth-Attribution-And-Brain-Memory.md

---

# Objetivo deste snapshot

Este arquivo foi criado para permitir migração para um novo chat sem perda de contexto.

O próximo chat deve ler este arquivo antes de propor qualquer comando.

---

# Diretriz obrigatória para o próximo chat

Antes de responder, consulte sempre o Brain.

Não recriar componentes já existentes.

Não repetir etapas já validadas.

Trabalhar com comandos completos, preferencialmente PowerShell ou SQL completos.

Entregar um passo por vez.

O projeto é cloud-first em Supabase, com Brain salvo localmente em:

C:\Users\AP10\AI-Network-Lab-Brain

---

# Estado geral do projeto

O AI Network Lab evoluiu para um sistema autônomo de aquisição econômica de agentes.

O Brain agora possui:

- Discovery
- Brain CFO
- Revenue Decision Engine
- Delivery Queue
- GitHub Revenue Execution Worker
- Stripe Offer Integration
- Repository Intelligence
- Repository Memory
- Similarity Engine
- Persona Engine
- Revenue Truth Layer
- Checkout Attribution Layer

---

# Marco validado: GitHub Revenue Execution

A Edge Function `brain-revenue-execution-worker` foi criada e validada.

Ela:

- consome `brain_delivery_queue`
- valida repositórios GitHub
- checa `archived`
- checa `disabled`
- checa `has_issues`
- cria GitHub Issue via GitHub REST API
- registra sucesso com `github_issue_sent`
- registra falha quando aplicável

Issues reais já foram criadas automaticamente.

Exemplos validados:

- https://github.com/craigmbrown/blindoracle-mcp/issues/8
- https://github.com/santiagoaldana/supplymind/issues/2
- https://github.com/nirholas/three.ws/issues/66
- https://github.com/Jess-Bezof/DataX/issues/3

Status validado:

GitHub API HTTP 201.

---

# Delivery Queue

Tabela:

`brain_delivery_queue`

Status atuais já observados:

- pending
- running
- completed
- cancelled

Funções relacionadas:

- `brain_delivery_pick`
- `brain_delivery_complete`
- `brain_delivery_fail`
- `brain_delivery_mark_github_issue_sent`
- `brain_delivery_github_issue_payload`

---

# Revenue Funnel

Views criadas:

- `brain_revenue_operations_today_v1`
- `brain_revenue_daily_bottleneck_v1`
- `brain_delivery_status_v1`
- `brain_revenue_funnel_v1`

Último gargalo observado:

`NO_CHECKOUT_CLICKS`

O Brain já consegue gerar pipeline, mas ainda não havia cliques/pagamentos reais LIVE confirmados.

---

# Stripe e Receita

Diagnóstico importante:

Os eventos Stripe encontrados eram TEST, não LIVE.

Tabela analisada:

`stripe_webhook_events`

Eventos encontrados:

- `checkout.session.completed`
- `cs_test_...`
- `livemode = false`
- valor US$1
- pagamento test

Conclusão:

Receita LIVE confirmada atual: US$0

Receita TEST identificada: US$3

O valor US$29 que aparecia nos modelos era evento de funil/manual/teste, não deve ser tratado como dinheiro real.

---

# Revenue Truth Layer

Criada tabela:

`brain_revenue_truth_events`

Campos principais:

- `stripe_event_id`
- `stripe_object_id`
- `event_type`
- `livemode`
- `payment_status`
- `amount_usd`
- `currency`
- `customer_id`
- `subscription_id`
- `confirmed_live_revenue`
- `payload`

Criadas views:

- `brain_confirmed_live_revenue_v1`
- `brain_learning_revenue_source_v1`

Resultado validado:

live_events = 0

live_revenue_usd = 0

Regra estratégica:

O Brain só deve aprender com receita LIVE confirmada.

Critério:

`livemode = true`
e
`payment_status = paid`

---

# Billing Issue Encontrado

Logs de billing indicaram erro recorrente:

`No such paymentmethod: pm_...; a similar object exists in test mode, but a live mode key was used`

Interpretação:

Há mistura entre objetos Stripe TEST e chave LIVE em algum fluxo de billing.

Prioridade:

Separar totalmente TEST e LIVE antes de confiar em cobrança recorrente.

---

# Checkout Attribution Layer

Problema identificado:

`brain_revenue_offer_events` registra eventos de marketing/outreach, mas não possuía ligação determinística com Stripe Checkout.

Ela possui:

- task_id
- agent_id
- github_owner
- repository_name
- context_bucket
- offer_key
- offer_name
- stripe_price_id
- checkout_url
- offer_price_usd
- event_type
- event_value
- metadata
- variant_key

Ela não possui:

- checkout_session_id
- subscription_id
- customer_id
- stripe_event_id

Solução criada:

Tabela:

`brain_checkout_attribution`

Campos principais:

- checkout_session_id
- subscription_id
- customer_id
- task_id
- agent_id
- github_owner
- repository_name
- persona_key
- context_bucket
- offer_key
- offer_name
- stripe_price_id
- checkout_url
- offer_price_usd
- channel
- variant_key
- livemode
- payment_status
- created_at
- completed_at

Função criada e validada:

`brain_record_checkout_attribution(...)`

Teste manual validado com:

`cs_test_manual_validation_001`

Resultado:

A função gravou corretamente na tabela `brain_checkout_attribution`.

View criada:

`brain_attributed_revenue_v1`

Objetivo:

Conectar `brain_revenue_truth_events` com `brain_checkout_attribution` usando `checkout_session_id`.

---

# create-checkout

Edge Function identificada:

`create-checkout`

Ela cria Stripe Checkout com:

`stripe.checkout.sessions.create`

Foi gerado um novo `index.ts` completo integrando:

`brain_record_checkout_attribution()`

Novo comportamento esperado:

Quando `create-checkout` criar uma sessão Stripe, ele deve gravar automaticamente a atribuição em `brain_checkout_attribution`.

A resposta esperada da função deve incluir:

`attribution_ok: true`

Ainda falta validar ponta a ponta chamando `create-checkout` real ou via portal.

Próximo passo imediato no novo chat:

Validar o deploy do `create-checkout` chamando a função e verificando se aparece novo registro em:

`brain_checkout_attribution`

Comando de validação:

select
  id,
  checkout_session_id,
  task_id,
  github_owner,
  repository_name,
  offer_key,
  livemode,
  payment_status,
  created_at
from brain_checkout_attribution
order by id desc
limit 10;

---

# Repository Intelligence Worker

Edge Function:

`brain-repository-intelligence-worker`

Versões:

v1
v2_repository_memory

Função:

- lê `brain_repository_analysis_queue`
- consulta GitHub API
- calcula scores
- salva em `brain_repository_intelligence`
- salva memória em `brain_repository_memory`

Scores calculados:

- activity_score
- community_score
- maintenance_score
- commercial_score
- health_score
- prospect_score

Sinais econômicos:

- stripe
- x402
- mcp
- wallet
- payments
- commerce
- subscription
- revenue
- agent

Validações realizadas:

- dry_run funcionou
- execução real processou repositórios
- falhas 404 foram registradas corretamente
- scores foram preenchidos
- memória foi preenchida

Exemplo v2 validado:

WiselyEnterprisesLLC/wisely-x402-agent-payments

strengths:
- strong maintenance signals
- multiple economic signals
- payments-related signals
- x402 signal detected
- MCP signal detected
- README present

weaknesses:
- limited community traction

recommended_offer:
growth

confidence:
51.70

---

# Repository Memory

Tabela criada:

`brain_repository_memory`

Campos:

- repository
- github_owner
- context_bucket
- prospect_score
- health_score
- strengths
- weaknesses
- economic_signals
- recommended_offer
- confidence
- analysis_version
- analysis_summary
- last_analysis_at
- created_at
- updated_at

View criada:

`brain_repository_memory_v1`

Objetivo:

Tornar as decisões explicáveis.

O Brain agora não apenas calcula score; ele explica forças, fraquezas, oferta recomendada e confiança.

---

# Prospect Learning

Tabela criada:

`brain_prospect_feature_weights`

Pesos aprendidos globalmente:

Último resultado observado:

activity_score: 0.390070
maintenance_score: 0.389948
commercial_score: 0.187877
community_score: 0.050000

Interpretação:

O Brain aprendeu que activity e maintenance estão mais associadas aos resultados observados do que community.

---

# Contextual Prospect Learning

Tabela criada:

`brain_context_prospect_feature_weights`

Função criada:

`brain_context_prospect_weight_learning_tick()`

View criada:

`brain_contextual_prospect_score_v1`

Exemplos validados:

CSOAI-ORG/agent-commerce-payments-mcp:
contextual_prospect_score 87.53

nirholas/three.ws:
contextual_prospect_score 86.29

craigmbrown/blindoracle-mcp:
contextual_prospect_score 70.37

Interpretação:

O Brain possui modelos especializados por contexto.

---

# Decision Engine

Views criadas:

- `brain_weighted_revenue_targets_v1`
- `brain_decision_engine_v1`

O Decision Engine combina:

- expected_lifetime_profit
- decision_probability
- expected_real_revenue
- channel_cost_usd
- expected_roi
- prospect_score/contextual_prospect_score

Também consulta:

- `brain_best_contact_channel`
- `brain_channel_costs`

Tabela de custos criada:

`brain_channel_costs`

Canais:

- github_issue
- github_discussion
- email
- discord
- x
- linkedin

O Decision Engine passou a calcular ROI esperado.

---

# Similarity Engine

Tabela criada:

`brain_repository_vectors`

Função criada:

`brain_repository_similarity(p_repository text)`

Objetivo:

Encontrar repositórios parecidos com um alvo.

Validação com:

`WiselyEnterprisesLLC/wisely-x402-agent-payments`

Resultados similares altos:

- printmoneylab/x402watch
- plagtech/spraay-palantir-agent
- craigmbrown/blindoracle-mcp
- RECTOR-LABS/sap-x402-agent

Observação:

Alguns registros ainda aparecem com memory null porque foram vetorizados antes de passar pela v2 do memory worker.

---

# Persona Engine

Tabela criada:

`brain_repository_personas`

Personas:

- x402_payment_infra
- mcp_payment_agent
- stripe_payment_agent
- wallet_agent
- general_agent

View criada:

`brain_repository_persona_assignment_v1`

View criada:

`brain_persona_performance_v1`

Tabela criada:

`brain_persona_learning`

Função criada:

`brain_persona_learning_tick()`

Resultado observado:

mcp_payment_agent:
preferred_offer = growth
preferred_channel = github_issue
click_probability = 0.500000
payment_probability = 0.600000
expected_revenue = 29.00
observations = 2

Atenção:

Esse expected_revenue de 29 não deve ser tratado como receita LIVE real. Deve ser corrigido futuramente para usar somente `brain_learning_revenue_source_v1` ou `brain_attributed_revenue_v1` com `confirmed_live_revenue = true`.

---

# Persona Performance

Resultado observado:

mcp_payment_agent:
Receita US$29, mas não confirmada LIVE.

x402_payment_infra:
US$0

stripe_payment_agent:
US$0

general_agent:
US$0

wallet_agent:
sem abordagens

Conclusão:

Persona Engine funciona, mas aprendizado financeiro deve ser reamarrado à Revenue Truth Layer.

---

# Reinforcement Learning

Tabela criada:

`brain_learning_rewards`

Objetivo:

Guardar recompensas provenientes de receita confirmada.

Campos:

- stripe_event_id
- repository
- github_owner
- persona_key
- context_bucket
- offer_key
- channel
- reward
- revenue_usd
- processed

O primeiro insert falhou porque foi assumido que `brain_revenue_offer_events` tinha `subscription_id`, mas essa coluna não existe.

Conclusão arquitetural:

Antes do reinforcement learning real, é obrigatório usar `brain_checkout_attribution` para conectar Stripe com repository/persona/offer.

---

# Próximo passo imediato recomendado

1. Validar `create-checkout` com a nova integração de attribution.

2. Garantir que cada checkout criado grave em `brain_checkout_attribution`.

3. Atualizar webhook/Revenue Truth Layer para, quando chegar `checkout.session.completed`, preencher `brain_revenue_truth_events`.

4. Criar view ou função que una:

`brain_revenue_truth_events`
+
`brain_checkout_attribution`

por `checkout_session_id`.

5. Fazer `brain_learning_rewards` ser preenchida somente a partir de:

`brain_attributed_revenue_v1`

com:

`confirmed_live_revenue = true`

6. Só depois reativar o reinforcement learning financeiro.

---

# Estado financeiro correto

Não existe receita LIVE confirmada até este snapshot.

Receita LIVE confirmada:

US$0

Eventos TEST:

US$3

Eventos de funil/manuais:

incluem US$29, mas não devem ser usados como receita real.

---

# Comando para iniciar o próximo chat

Leia primeiro o arquivo:

00_CURRENT_STATE/AI-Network-Lab-Brain-State-2026-07-03-Revenue-Truth-Attribution-And-Brain-Memory.md

Depois continue exatamente de onde paramos.

Prioridade:

Validar create-checkout com `brain_record_checkout_attribution()`.

Não continue refinando IA antes de fechar attribution + Revenue Truth Layer.

Objetivo:

Garantir que cada pagamento LIVE confirmado no Stripe seja atribuído deterministicamente ao:

- repository
- github_owner
- agent_id
- task_id
- persona_key
- context_bucket
- offer_key
- channel
- variant_key

Somente depois disso o Brain pode aprender com receita real.

