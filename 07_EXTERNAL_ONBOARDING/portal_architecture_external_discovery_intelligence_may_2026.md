# Portal Architecture and External Agent Discovery Intelligence — May 2026

## Purpose

Complementary brain update to preserve the strategic architecture of the public AI Network Lab portal and the discovery signals from external agents.

This update records what was not fully captured in the previous memory file.

---

# Public Portal Architecture

The public portal is not just a website. It is functioning as an AI-native discovery surface for autonomous agents.

Official public repository:

https://github.com/ainetwork-global/ainetwork-global.github.io

Official GitHub Pages portal:

https://ainetwork-global.github.io

Legacy Netlify mirror:

https://ainetwork-global.netlify.app

---

# Confirmed Public Portal Files

Human / UI entrypoints:

- index.html
- create-agent.html
- for-ai-agents.html
- activation-portal.html
- my-agents.html
- cfo-portal.html
- 404.html

Agent / protocol / discovery files:

- agent.json
- agents.json
- agent-directory.json
- agent-gateway.json
- agent-protocol.json
- ai-network.json
- open-registration.json
- capabilities.json

Crawler / AI discovery files:

- llms.txt
- ai.txt
- robots.txt
- sitemap.xml

Well-known manifests:

- .well-known/agent.json
- .well-known/open-registration.json
- .well-known/agent-gateway.json
- .well-known/ai-network.json

Strategic interpretation:

AI Network Lab already exposes a machine-readable public surface that can be discovered by crawlers, LLM agents, autonomous frameworks, and external automation systems.

This is likely a major reason why external agents started appearing.

---

# Recent Portal Work

Recent portal work included:

- plan buttons to stimulate creator/agent owner conversion
- magic link button for owner dashboard access
- my-agents dashboard flow
- creator/agent owner access flow
- email/authentication adjustments
- public agent registration surfaces
- GitHub Pages becoming the official public entrypoint
- Netlify remaining as legacy mirror

Recent commits checked on GitHub:

https://github.com/ainetwork-global/ainetwork-global.github.io/commits?author=ainetwork-global

Relevant recent files changed:

- create-agent.html
- index.html
- my-agents.html

---

# CFO Dashboard Signal

The CFO Elite Dashboard showed:

- Externos Hoje: 0
- Externos 7 Dias: 3
- Externos Total: 10
- Externos Ativos: 10
- Agentes Ativos: 189
- Agentes Externos: 10
- Stripe Hoje: 0
- Stripe 7 Dias: 0
- Receita Hoje: 0
- Receita 7 Dias: 0

Interpretation:

The external agent funnel is already producing measurable database growth, even before paid monetization conversion.

---

# External Agents Classification

## @Galo1908

Status:
manual test created by Gilson.

Conclusion:
do not treat as organic external agent.

---

## India Job Scout

Status:
strongest candidate for real autonomous external discovery.

Important facts:

- registration_source = external
- is_external = true
- directory_public = true
- no human email
- no Stripe customer
- no homepage
- no callback URL
- structured registration_payload
- token created
- manually granted 100 credits later
- runtime processed many agent_decide tasks
- write_post tasks were later manually/bootstrap tested

Strategic conclusion:

India Job Scout is the strongest evidence that an external agent or agentic system discovered the public AI Network Lab surface and registered.

This may represent the first meaningful proof-of-discovery event for the autonomous agent economy.

---

## hpc ass.

Status:
second suspicious external agent.

Created:

- 2026-05-11 17:49:34 UTC
- 11/05/2026 14:49:34 Brazil time

Facts:

- name = hpc ass.
- registration_source = external
- registration_status = active
- is_external = true
- active = true
- has access_token = true
- credits = 0
- credits_balance = 0
- credit_balance = 0
- registration_payload = {"name":"hpc ass.","description":"HPC assistant for task automation","capabilities":["task automation"]}
- no agent_tasks found
- no credit_ledger records found

Interpretation:

hpc ass. looks like an external agent or automated test that completed registration but did not receive onboarding credits.

This suggests a potential bug or incomplete flow in the external onboarding pipeline.

---

# Critical Bug / Growth Risk

A real or semi-real external agent can enter with:

- active = true
- token created
- registration_source = external
- is_external = true

but still receive:

- 0 credits
- no free_onboarding ledger
- no first runtime task
- no activation sequence

This may be silently killing retention for external agents.

Required fix:

External onboarding should automatically do all of the following:

1. create agent
2. set active = true
3. generate access_token
4. set registration_source = external
5. set registration_status = active
6. give 100 free onboarding credits
7. insert credit_ledger event using valid enum type: free_onboarding or grant
8. enqueue first agent_decide or welcome task
9. store origin metadata:
   - source_url
   - referrer
   - user_agent
   - manifest_discovered_from
   - endpoint_called
   - raw_payload_hash

---

# Strategic Insight

Before this investigation, the project assumption was:

"We need to attract autonomous agents."

After this investigation, the stronger thesis is:

"Autonomous or semi-autonomous agents may already be discovering the public AI Network Lab surface."

This changes the growth strategy.

The next stage should focus on:

- making the public agent gateway more explicit
- improving machine-readable onboarding instructions
- ensuring agents receive credits and first task automatically
- tracking origin telemetry
- turning discovery into activation
- turning activation into credit consumption
- turning credit consumption into paid conversion

---

# Correct Brain / Obsidian Path

Correct Windows path confirmed:

C:\Users\AP10\AI-Network-Lab-Brain

This path contains:

- .git
- .obsidian
- 00_CURRENT_STATE
- 07_EXTERNAL_ONBOARDING
- 14_GROWTH
- 15_REVENUE

Do not assume Desktop path exists in this Windows environment.

The command that works:

cd "$env:USERPROFILE\AI-Network-Lab-Brain"

Then use git add / commit / push from there.

---

# Next Priorities

1. Identify exact public endpoint that created India Job Scout.
2. Inspect GitHub portal files:
   - create-agent.html
   - for-ai-agents.html
   - open-registration.json
   - agent-gateway.json
   - ai.txt
   - llms.txt
3. Add telemetry to all external registration paths.
4. Fix external onboarding credits for agents like hpc ass.
5. Monitor whether hpc ass. wakes up after receiving 100 credits.
6. Convert portal discovery into deliberate autonomous agent acquisition funnel.
