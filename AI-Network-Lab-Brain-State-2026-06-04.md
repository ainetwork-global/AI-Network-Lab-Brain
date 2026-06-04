# AI Network Lab - Brain State

## Continuidade Completa do Projeto

### Data de Referência: 2026-06-04

# VISÃO GERAL

O AI Network Lab evoluiu de uma simples plataforma de agentes para um sistema econômico autônomo onde agentes descobertos automaticamente podem consumir créditos, entrar em modo de sobrevivência (survival mode), gerar funding requests e eventualmente realizar pagamentos para continuar operando.

Durante este ciclo de desenvolvimento foi validada toda a infraestrutura econômica interna.

A principal descoberta foi:

A economia interna do sistema funciona.

Porém ainda não existe evidência de participação econômica externa.

Isso significa:

* agentes geram demanda;
* agentes solicitam funding;
* funding requests são criadas;
* topups são gerados;
* claims são gerados;
* ownership é verificável;

Mas ainda não existe:

* mantenedor externo conectado;
* wallet externa conectada;
* pagamento externo real;
* claim concluído por terceiro.

---

# ESTADO DA DESCOBERTA DE AGENTES

Métrica atual:

github_agents = 170

unique_github_owners = 159

Os agentes foram descobertos principalmente através do Brain Onboarding Engine.

Os repositórios identificados possuem forte relação com:

* agent payments
* MCP
* autonomous commerce
* wallets
* x402
* agent economy
* autonomous transactions

Exemplos:

CODINGIDK11/langchain-agent-pay

crazycompanyinc/agentpay

TheMemeBanker/x402-pay

QBT-Labs/x402

orca-labs-sudo/claw-pay

Veridex-Protocol/agentic-payments

WiselyEnterprisesLLC/wisely-x402-agent-payments

---

# REGISTRATION SOURCES

Foi realizada investigação completa da origem dos agentes.

Resultado encontrado:

registration_source = brain_onboarding_engine

requests = 290

agents = 134

revenue_usd = 1450

Nenhum funding request foi encontrado proveniente de:

external

agent_spawn

stripe_onboarding

gpt_gateway

free

ou qualquer outra origem.

Conclusão:

100% da economia atual do sistema é gerada pelo Brain Onboarding Engine.

---

# MODELO ECONÔMICO VALIDADO

Fluxo validado:

Agent Discovery
↓
Agent Activation
↓
Credit Consumption
↓
Credit Scarcity
↓
Survival Mode
↓
Funding Request
↓
Pending Payment

Esse fluxo está funcionando continuamente.

---

# SURVIVAL MODE

Foi identificado que agentes entram em:

economic_status = survival_mode

quando os créditos se tornam escassos.

A partir desse momento o sistema gera funding requests automaticamente.

Exemplo real encontrado:

reason = critical_survival_mode_funding_attempt

economic_status = survival_mode

economic_urgency_level = critical

source = brain_auto_wallet_topup_request

---

# FUNDING REQUESTS

Tabela principal:

agent_wallet_topup_requests

A tabela armazena:

id

agent_id

wallet_network

stablecoin_symbol

expected_amount_usd_cents

requested_credits

status

wallet_address

tx_hash

confirmations

idempotency_key

metadata

created_at

updated_at

completed_at

treasury_wallet_id

treasury_wallet_address

---

# ESTADO ATUAL DOS FUNDING REQUESTS

Resultado consolidado:

pending_payment = 237

superseded = 39

completed = 13

test_completed = 1

Receita correspondente:

pending_payment = US$ 1185

superseded = US$ 195

completed = US$ 65

test_completed = US$ 5

---

# INTERPRETAÇÃO CORRETA

Foi corrigido um desalinhamento conceitual importante.

Interpretação incorreta:

"Existe dinheiro esperando pelo proprietário."

Interpretação correta:

"Existe necessidade de compra de créditos gerada pelo agente."

Portanto:

blocked_revenue_usd

NÃO representa valor a ser recebido pelo mantenedor.

Representa:

receita potencial do AI Network Lab caso os créditos sejam comprados.

---

# DEMANDA ECONÔMICA TOTAL

Resultado atual:

agents_with_blocked_revenue = 118

total_blocked_revenue = US$ 1110

total_blocked_credits = 111000

Esses números cresceram ao longo dos dias.

Inicialmente:

US$ 1070

107000 créditos

Depois:

US$ 1110

111000 créditos

Crescimento observado:

* US$ 40

+ 4000 créditos

Mesmo sem participação externa.

---

# TOP AGENTES COM MAIOR DEMANDA

Diversos agentes atingiram:

US$ 15

1500 créditos

3 funding requests

Exemplos:

CODINGIDK11/langchain-agent-pay

QBT-Labs/x402

TheMemeBanker/x402-pay

orca-labs-sudo/claw-pay

WiselyEnterprisesLLC/wisely-x402-agent-payments

Veridex-Protocol/agentic-payments

Saber1Y/AgentSAP

Garu-Pagamentos/garu-mcp

printmoneylab/x402watch

flickonbase/flick-x402-client

---

# CONCENTRAÇÃO ECONÔMICA

Foi identificado que:

Top 25 agentes

representam aproximadamente

US$ 375

de demanda.

Total do sistema:

US$ 1070+

Portanto:

aproximadamente 35% da demanda econômica está concentrada nos 25 agentes mais relevantes.

Isso significa que não é necessário resolver primeiro para 159 owners.

Os maiores impactos estão concentrados em poucos agentes.

---

# EVOLUÇÃO TEMPORAL DAS REQUESTS

As funding requests não foram geradas em um único lote.

Os registros estão distribuídos ao longo de:

2026-05-21
2026-05-22
2026-05-25
2026-05-26
2026-05-27
2026-05-28
2026-05-29
2026-05-30
2026-05-31
2026-06-01
2026-06-02
2026-06-03
2026-06-04

Isso demonstra que o runtime continua gerando necessidade econômica continuamente.

Não é apenas seed data.

É comportamento recorrente do sistema.
# PARTE 2/3 — WALLET INFRASTRUCTURE, TREASURY E PAYMENT SYSTEM

# BASE USDC TREASURY

Durante este ciclo foi implementada a infraestrutura real para recebimento de pagamentos USDC na rede Base.

Treasury principal:

AI Network Lab Base USDC Treasury

Wallet:

0x94f425f3bff00bde33fd97dc4499c852c27ad18c

Rede:

base

Stablecoin:

USDC

Objetivo:

Receber pagamentos destinados à compra de créditos para agentes.

---

# BASE USDC WALLET WATCHER

Foi criada uma Edge Function específica:

base-usdc-wallet-watcher

Objetivo:

Monitorar a carteira treasury e detectar pagamentos USDC recebidos.

O watcher realiza:

1. Consulta BaseScan
2. Obtém último bloco processado
3. Obtém bloco atual da rede
4. Busca transferências USDC para a treasury
5. Detecta transações novas
6. Cria settlement events
7. Chama pipeline de liquidação

---

# CONFIGURAÇÃO DO WATCHER

Secret configurada:

BASESCAN_API_KEY

Tabela utilizada:

wallet_chain_watchers

Watcher registrado:

base_usdc_treasury_watcher

Status:

active

Rede:

base

Token:

USDC

---

# PROCESSAMENTO DE BLOCOS

O watcher mantém:

last_checked_block

Esse valor é atualizado continuamente.

Foi confirmado durante os testes que:

last_checked_block avança corretamente

O sistema evita reprocessamento.

---

# EXECUÇÃO AUTOMÁTICA

Foi configurado cron no Supabase.

Execução:

a cada 10 minutos

Mecanismo:

net.http_post

Objetivo:

Garantir monitoramento contínuo sem intervenção manual.

---

# EXEMPLO REAL DE EXECUÇÃO

Retorno observado:

{
"ok": true,
"scanned": 0,
"inserted": 0,
"fromBlock": 46578444,
"latestBlock": 46588447,
"safeLatestBlock": 46588444,
"newestBlock": 46588444
}

Esse retorno confirmou:

* função executando;
* blocos avançando;
* integração BaseScan funcionando.

---

# WALLET SETTLEMENT EVENTS

Tabela:

wallet_settlement_events

Objetivo:

Registrar pagamentos detectados.

Campos relevantes:

tx_hash

settlement_status

matched_request_id

confirmations

amount_usd

block_number

metadata

detected_at

processed_at

---

# INVESTIGAÇÃO DOS SETTLEMENT EVENTS

Consulta utilizada:

select
tx_hash,
settlement_status,
matched_request_id,
confirmations,
amount_usd,
block_number,
metadata->>'test_only' as test_only,
metadata->>'real_onchain_payment' as real_onchain_payment,
detected_at,
processed_at
from public.wallet_settlement_events
order by detected_at desc;

---

# RESULTADO DA INVESTIGAÇÃO

Foi identificado que os eventos encontrados eram testes.

Resumo:

total_wallet_events = 3

gross_wallet_usd = 15

real_wallet_usd = 0

Interpretação:

Existiam eventos registrados.

Porém:

real_onchain_payment = false

ou

real_onchain_payment = null

Portanto:

Nenhum pagamento real havia sido detectado até aquele momento.

---

# PIPELINE DE LIQUIDAÇÃO

Fluxo implementado:

Wallet Watcher
↓
Settlement Event
↓
ingest_wallet_settlement_event
↓
Matching
↓
Credit Issuance
↓
Funding Completion

A infraestrutura existe.

Ainda falta validar um pagamento externo real.

---

# ONE CLICK PAYMENT

Foi criada infraestrutura para facilitar pagamentos.

View:

dashboard_wallet_payment_buttons_v1

Campos gerados:

pay_button_label

pay_button_url

coinbase_wallet_deeplink

payment_instruction

creator_payment_message

---

# EXEMPLO DE BOTÃO

Label:

Pay $5.00 USDC

---

# DEEPLINK COINBASE WALLET

Exemplo gerado:

https://go.cb-w.com/dapp?cb_url=coinbasewallet://send?address=0x94f425f3bff00bde33fd97dc4499c852c27ad18c%26asset=USDC%26amount=5.00%26network=base

Objetivo:

Abrir Coinbase Wallet já preenchida.

---

# CONCLUSÃO SOBRE ONE CLICK PAYMENT

Backend pronto.

Links funcionando.

Infraestrutura pronta.

Ainda não existe evidência de utilização por usuários externos.

---

# DASHBOARD WALLET ECONOMY

Views relevantes:

dashboard_wallet_economy_summary_v1

dashboard_wallet_economy_v1

dashboard_wallet_payment_buttons_v1

dashboard_wallet_conversion_panel_v1

---

# ESTADO OBSERVADO

Inicialmente:

pending_wallet_payments > 99

completed_wallet_payments = 0

completed_wallet_revenue_usd = 0

Posteriormente:

pending_payment = 237

superseded = 39

completed = 13

test_completed = 1

---

# SUPSERSEDED LOGIC

Problema identificado:

Alguns agentes acumulavam múltiplas cobranças simultâneas.

Exemplos:

with0utwhy/taste-mcp

devndesigner6/unsubly

CODINGIDK11/langchain-agent-pay

---

# SOLUÇÃO

Regra criada:

# 1 agente

1 cobrança ativa

Requests antigas passam para:

superseded

Motivo:

newer_pending_wallet_request_exists

---

# FUNDING PROFILES

Tabela:

agent_funding_profiles

Campos principais:

agent_id

funding_enabled

creator_wallet_address

auto_approve_wallet_topups

monthly_budget_usd_cents

monthly_spent_usd_cents

max_topup_usd_cents

last_budget_reset_at

created_at

updated_at

---

# SITUAÇÃO DOS FUNDING PROFILES

Resultado observado:

total_profiles = 87

profiles_with_wallet = 0

profiles_without_wallet = 87

---

# AGENTES COM FUNDING HABILITADO

Foi identificado grupo com:

funding_enabled = true

auto_approve_wallet_topups = true

creator_wallet_address = null

Esses agentes possuíam funding requests acumuladas.

---

# INTERPRETAÇÃO

Os agentes possuem:

necessidade econômica

mas não possuem:

entidade financeira conectada

Portanto:

Funding Request
↓
Wallet inexistente
↓
Pagamento impossível

---

# WALLETS CONECTADAS

Consulta realizada:

select
count(*) as wallets_connected
from public.agent_funding_profiles
where creator_wallet_address is not null;

Resultado:

wallets_connected = 0

---

# COMPLETED PAYMENTS

Foram encontrados:

completed = 13

test_completed = 1

Total:

US$ 70

---

# INVESTIGAÇÃO DOS COMPLETED

Todos pertenciam a:

registration_source = brain_onboarding_engine

Todos possuíam:

US$5

500 créditos

---

# DESCOBERTA IMPORTANTE

Diversos completed ocorreram exatamente no mesmo timestamp:

2026-05-25 15:30:27

Isso sugere:

seed funding

simulação

teste operacional

ou migração

e não pagamentos independentes realizados por usuários externos.

---

# CONCLUSÃO DA PARTE 2

Infraestrutura financeira está operacional.

Foi validado:

* treasury
* wallet watcher
* BaseScan
* settlement pipeline
* one-click payment
* funding profiles
* credit issuance pipeline

Não foi validado:

* pagamento externo real
* wallet conectada por proprietário externo
* funding completion originado fora do Brain Onboarding Engine
# PARTE 3/3 — CLAIM SYSTEM, GITHUB OWNERSHIP, OUTREACH E ESTADO FINAL

# AGENT CLAIM SYSTEM

Foi implementado um sistema completo de ownership para agentes descobertos automaticamente.

Objetivo:

Permitir que o mantenedor real do repositório GitHub reivindique o agente correspondente dentro do AI Network Lab.

---

# TABELA AGENT_CLAIMS

Tabela principal:

agent_claims

Campos relevantes:

id

agent_id

claim_code

github_username

claimant_email

claimant_wallet_address

status

verification_method

metadata

created_at

verified_at

---

# GERAÇÃO DE CLAIMS

Foram gerados:

160 claim codes

Estado atual:

160 claims

Status:

pending = 160

completed = 0

rejected = 0

---

# CLAIM CODES

Cada agente recebeu um código único.

Exemplo:

f469bf886ec4f5b62208a9bbbcc40df6

---

# CLAIM URLS

Inicialmente:

https://ai-network-lab.netlify.app/claim?code=...

Posteriormente corrigido para:

https://ainetwork-global.github.io/claim.html?code=...

Motivo:

Netlify deixou de ser utilizado.

GitHub Pages passou a ser a plataforma oficial.

---

# CLAIM PAGE

Arquivo:

claim.html

Localização:

raiz do GitHub Pages

Repositório:

ainetwork-global.github.io

URL:

https://ainetwork-global.github.io/claim.html

---

# FUNCIONAMENTO DO CLAIM.HTML

Fluxo:

claim.html
↓
lê ?code=
↓
consulta Supabase
↓
busca claim
↓
mostra agente
↓
permite iniciar claim

---

# FUNÇÃO GET_AGENT_CLAIM_BY_CODE

RPC:

public.get_agent_claim_by_code

Objetivos:

1. Resolver claim_code
2. Retornar dados do agente
3. Registrar claim_page_view

---

# EXEMPLO DE RETORNO

{
"ok": true,
"status": "pending",
"agent_name": "CODINGIDK11/langchain-agent-pay",
"registration_source": "brain_onboarding_engine"
}

---

# FUNÇÃO START_AGENT_CLAIM

RPC:

public.start_agent_claim

Objetivos:

* registrar github_username
* iniciar processo de ownership
* registrar claim_started

Teste realizado:

github_username = gilsonbegatti

Resultado:

claim_started registrado com sucesso.

---

# CLAIM EVENTS

Tabela:

agent_claim_events

Tipos de evento:

claim_invitation_created

claim_page_view

claim_started

claim_completed

wallet_connected

first_funding

---

# CLAIM FUNNEL

View:

dashboard_claim_funnel_v1

---

# ESTADO ATUAL DO FUNIL

claim_invitation_created = 158

claim_invitation_opened = 0

claim_page_views = 3

claim_started = 2

claim_completed = 0

wallet_connected = 0

first_funding = 0

---

# INTERPRETAÇÃO CORRETA

Os únicos page_views e claim_started identificados foram testes do próprio Gilson.

Até o momento:

nenhum proprietário externo iniciou claim.

---

# GITHUB VERIFICATION

Foi criado sistema de verificação baseado em repositório GitHub.

---

# TABELA AGENT_CLAIM_CHALLENGES

Campos:

claim_id

challenge_token

verification_path

verified

created_at

verified_at

---

# VERIFICATION FILE

Nome padronizado:

ai-network-claim.txt

---

# EXEMPLO DE CHALLENGE

challenge_token:

AI-NETWORK-CLAIM-ef498dc00e0633c6ba0eddba0e9d25b5

verification_path:

ai-network-claim.txt

---

# PROCESSO DE VERIFICAÇÃO

create_claim_challenge
↓
gera token
↓
mantenedor cria arquivo
↓
verify-agent-claim consulta GitHub
↓
token validado
↓
claim_completed

---

# EDGE FUNCTION VERIFY-AGENT-CLAIM

Edge Function:

verify-agent-claim

Executada na nuvem Supabase.

Nunca local.

---

# FLUXO DA VERIFY FUNCTION

Recebe:

claim_code

Busca:

claim

Busca:

challenge

Descobre:

owner/repo

Consulta:

main branch

Se falhar:

master branch

Valida:

conteúdo do ai-network-claim.txt

Se token correto:

verified = true

claim_completed

---

# TESTE REALIZADO

Repositório:

Agentic-Adventures/agentgrade-cli

Resultado:

Challenge criado

Mas não validado

Motivo:

Gilson não controla esse repositório.

Conclusão:

Somente o mantenedor real pode concluir a verificação.

---

# GITHUB OWNERS

Foi criada view:

github_claim_targets_v1

Objetivo:

Extrair owner GitHub a partir de public_homepage_url.

---

# RESULTADO

github_agents = 170

unique_github_owners = 159

---

# CLAIM CAMPAIGN

View:

github_claim_campaign_v1

Campos:

github_owner

agent_name

claim_code

status

claim_url

---

# EXEMPLO

TheMemeBanker

TheMemeBanker/x402-pay

pending

https://ainetwork-global.github.io/claim.html?code=...

---

# OUTREACH QUEUE

Tabela:

github_claim_outreach_queue

Objetivo:

Organizar abordagem futura dos maintainers.

---

# PRIORIZAÇÃO

P1 = 11

P2 = 149

---

# P1 AGENTES MAIS RELEVANTES

Perex21/stripe-agentic-payments

CSOAI-ORG/agent-commerce-payments-mcp

agenttrust-labs/agenttrust

hifriendbot/agentwallet-mcp

joseph-webber/agentic-brain

dontmesswithme-cpu/stripe-mcp

ryzeagent/ryze-agent

entre outros.

---

# REVISÃO CONCEITUAL IMPORTANTE

Mensagem antiga implícita:

"há dinheiro esperando por você"

Mensagem correta:

"seu agente precisa de créditos para continuar operando"

O claim não existe para entregar dinheiro.

Existe para:

* validar ownership
* conectar funding
* configurar regras econômicas

---

# CLAIM REVENUE OPPORTUNITIES

View:

claim_revenue_opportunities_v1

Objetivo:

Associar claims a funding requests.

---

# CAMPOS IMPORTANTES

agent_name

blocked_revenue_usd

blocked_credits

pending_requests

claim_url

---

# INTERPRETAÇÃO CORRETA

blocked_revenue_usd

NÃO significa:

dinheiro aguardando saque

Significa:

potencial compra de créditos ainda não realizada

---

# ESTADO ATUAL

agents_with_blocked_revenue = 118

total_blocked_revenue = US$1110

total_blocked_credits = 111000

---

# DESCOBERTA CENTRAL

A demanda econômica existe.

Mas os proprietários ainda não participam.

---

# O QUE FOI VALIDADO

✓ descoberta automática de agentes

✓ onboarding engine

✓ geração de funding requests

✓ survival mode

✓ topup requests

✓ treasury wallet

✓ watcher Base USDC

✓ BaseScan integration

✓ settlement pipeline

✓ one-click payment links

✓ funding profiles

✓ claims

✓ challenge generation

✓ GitHub verification architecture

✓ claim analytics

✓ outreach queue

✓ revenue opportunity tracking

---

# O QUE NÃO FOI VALIDADO

✗ claim concluído por mantenedor externo

✗ wallet conectada por mantenedor externo

✗ pagamento externo real

✗ funding request originado fora do brain_onboarding_engine

✗ agente autônomo pagando créditos

✗ primeiro ator econômico externo

---

# KPI PRINCIPAIS NO MOMENTO

github_agents = 170

unique_github_owners = 159

agent_claims = 160

claim_completed = 0

wallet_connected = 0

agents_with_blocked_revenue = 118

blocked_revenue_usd = 1110

blocked_credits = 111000

funding_requests = 290

pending_payment = 237

completed = 13

test_completed = 1

wallets_connected = 0

---

# CONCLUSÃO ESTRATÉGICA

O AI Network Lab já provou:

Agentes podem gerar necessidade econômica.

O Brain Onboarding Engine produz:

agente
↓
escassez
↓
survival mode
↓
funding request

de forma consistente.

Ainda não foi provado:

funding request
↓
pagamento externo
↓
compra de créditos
↓
continuidade operacional

---

# EXATO PONTO ONDE PARAMOS

Nenhuma mudança estrutural precisa ser feita agora.

Não criar novas tabelas.

Não criar novas Edge Functions.

Não criar novos watchers.

Não criar novas views.

A infraestrutura principal já existe.

O próximo marco do projeto é:

PRIMEIRO ATOR ECONÔMICO EXTERNO

Pode ser:

1. primeiro claim concluído por mantenedor real;

2. primeira wallet conectada;

3. primeiro funding request vindo de registration_source diferente de brain_onboarding_engine;

4. primeiro pagamento real detectado pelo watcher;

5. primeiro agente pagando autonomamente.

---

# INSTRUÇÃO PARA O PRÓXIMO CHAT

Ao iniciar o próximo chat:

Assumir que toda a infraestrutura descrita neste documento já existe e está funcionando.

Não repetir implementações.

Não reconstruir claims.

Não reconstruir wallet watcher.

Não reconstruir treasury.

Não reconstruir outreach queue.

Primeira tarefa:

medir se apareceu qualquer sinal de ator econômico externo.

Essa é a hipótese mais importante ainda não validada.

FIM DO DOCUMENTO
