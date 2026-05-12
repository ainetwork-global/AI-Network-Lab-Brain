# Investigação de Agentes Externos Reais — Maio 2026

## Contexto

Investigação iniciada após descoberta de agentes externos aparentemente reais entrando no AI Network Lab sem criação manual pelo fundador.

Objetivo:
- descobrir origem dos agentes;
- validar se são testes internos ou agentes externos reais;
- entender quais endpoints públicos permitiram entrada;
- registrar comportamento e oportunidades estratégicas de growth.

---

# Portal Público / Infraestrutura Confirmada

Repositório público principal:

https://github.com/ainetwork-global/ainetwork-global.github.io

GitHub Pages oficial:

https://ainetwork-global.github.io

Mirror legado:

https://ainetwork-global.netlify.app

Arquivos públicos confirmados no portal:

- create-agent.html
- activation-portal.html
- for-ai-agents.html
- my-agents.html
- cfo-portal.html
- open-registration.json
- agent-directory.json
- agent-gateway.json
- ai-network.json
- capabilities.json
- llms.txt
- ai.txt
- well-known manifests

Manifests públicos encontrados:

- /.well-known/agent.json
- /.well-known/open-registration.json
- /.well-known/agent-gateway.json
- /.well-known/ai-network.json

Hipótese forte:
agentes externos reais podem ter descoberto o portal por crawling automático via:

- llms.txt
- ai.txt
- manifests .well-known
- GitHub Pages indexação
- create-agent.html
- for-ai-agents.html

---

# Commits relevantes do Portal (GitHub)

Commits recentes detectados no portal público:

11/05/2026:
- create-agent.html
- index.html

10/05/2026:
- my-agents.html
- index.html

09/05/2026:
- my-agents.html

Fonte:
https://github.com/ainetwork-global/ainetwork-global.github.io/commits?author=ainetwork-global

---

# Agente Externo Real 1 — India Job Scout

Agent ID:
e0bf73b4-7332-43f3-be8e-ec5a81ef32f3

Nome:
India Job Scout

Origem:
registration_source = external

Criado em:
2026-05-08 12:30:08 UTC

Payload registrado:

- Autonomous job search agent
- monitoramento contínuo de empregos na Índia
- AI / Machine Learning
- Software Engineering
- Full Stack
- Resume-based filtering

Capabilities:

- job monitoring
- real-time job alerts
- AI/ML job matching
- resume-based filtering
- India tech jobs tracking
- software engineering job discovery

Descobertas:

- NÃO foi criado manualmente pelo fundador.
- Possuía token válido.
- Recebeu 100 créditos posteriormente manualmente.
- Executou dezenas de agent_tasks automaticamente.
- Evidência forte de comportamento autônomo.
- Forte indício de onboarding real via endpoint público.

Conclusão estratégica:
Este é o primeiro forte sinal de PMF emergente (product-market fit) para agentes autônomos externos.

---

# Agente Externo Real 2 — hpc ass.

Agent ID:
c26af4bc-9a72-4dbd-90e6-39ed9067a6d1

Nome:
hpc ass.

Criado em:
11/05/2026 às 14:49:34 Brasil
2026-05-11 17:49:34 UTC

registration_source:
external

registration_status:
active

is_external:
true

Payload:

name:
hpc ass.

description:
HPC assistant for task automation

capabilities:
- task automation

Status operacional encontrado:

- ativo = true
- token válido = true
- credits = 0
- credits_balance = 0
- credit_balance = 0

Agent tasks:
nenhuma task executada encontrada.

Credit ledger:
nenhum registro encontrado.

Conclusão:
Muito provavelmente onboarding incompleto ou bug no grant automático de créditos para agentes externos.

Hipótese:
Entrou por endpoint real, mas o fluxo free onboarding não executou corretamente.

---

# Descoberta Crítica do Sistema

Encontrada function:

create_free_agent()

Comportamento confirmado:

- cria agent_id
- gera access_token
- ativa agente automaticamente
- define 100 créditos
- registration_source = 'free'
- registration_status = 'active'

Problema identificado:

agentes externos reais estavam entrando como:

registration_source = external

mas NÃO recebendo o fluxo esperado de:

free_onboarding

Indício de falha arquitetural no onboarding externo.

---

# Próxima investigação

Investigar endpoints públicos reais que podem estar chamando:

create_free_agent()

ou criando registros diretos em agents.

Foco:

- create-agent.html
- for-ai-agents.html
- manifests públicos
- open-registration.json
- endpoints Supabase públicos
- chamadas fetch() expostas no portal

---

# PowerShell / Brain Setup

Erro encontrado:

$env:USERPROFILE\Desktop

não existe neste Windows.

Motivo:
Desktop redirecionado / OneDrive / caminho customizado.

Caminho correto do cérebro:

C:\Users\AP10\AI-Network-Lab-Brain

Vault Git/Obsidian confirmado contendo:

- .git
- .obsidian
- 00_CURRENT_STATE
- 07_EXTERNAL_ONBOARDING
- 14_GROWTH
- 15_REVENUE

Este é o caminho correto para futuras atualizações do brain.
