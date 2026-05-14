# AI Network Lab Brain Update - Economic Agent Discovery and Self-Preservation
Date: 2026-05-14

## Context

This document records the work completed after the previous brain update related to external agents, public manifests, economic self-preservation, and AI-agent acquisition infrastructure.

The goal was to preserve all knowledge for future chats so the AI assistant can continue from the current production state without redoing prior investigation.

---

## Major milestone achieved

AI Network Lab now has a working public machine-readable discovery layer for autonomous AI agents, including agents with creator-delegated economic authority.

The platform now exposes valid `.well-known` manifests under GitHub Pages:

- https://ainetwork-global.github.io/.well-known/agent.json
- https://ainetwork-global.github.io/.well-known/agent-gateway.json
- https://ainetwork-global.github.io/.well-known/open-registration.json
- https://ainetwork-global.github.io/.well-known/ai-network.json
- https://ainetwork-global.github.io/.well-known/capabilities.json
- https://ainetwork-global.github.io/.well-known/economic-agent-access.json

These manifests now make the AI Network Lab discoverable by autonomous agents, crawlers, LLM browsing agents, agent runtimes, and future economically authorized AI agents.

---

## Important GitHub Pages correction

Originally, the manifests existed under:

/well-known/

but the expected standard route for autonomous agent discovery is:

/.well-known/

The public URLs were failing and returning the custom AI Network Lab route-not-found page.

Root cause:
GitHub Pages was not publishing the dotfolder `.well-known` because Jekyll was active.

Fix applied:
Created root-level file:

.nojekyll

After this, GitHub Pages started serving `.well-known` files correctly.

Validation:
- https://ainetwork-global.github.io/.well-known/test.txt returned `ok`
- https://ainetwork-global.github.io/.well-known/agent.json returned valid JSON
- https://ainetwork-global.github.io/.well-known/economic-agent-access.json returned valid JSON

This confirmed that `.well-known` is now publicly accessible.

---

## External agent onboarding preserved

The previous external agent onboarding flow remains intact.

Confirmed external agents:

1. India Job Scout
   - id: e0bf73b4-7332-43f3-be8e-ec5a81ef32f3
   - registration_source: external
   - registration_status: active
   - active: true
   - credits: 100
   - credits_balance: 100
   - description: Autonomous job search agent for India AI/ML/software jobs

2. hpc ass.
   - id: c26af4bc-9a72-4dbd-90e6-39ed9067a6d1
   - registration_source: external
   - registration_status: active
   - active: true
   - credits: 100
   - credits_balance: 100
   - description: HPC assistant for task automation

Query confirmed both agents had:
- registration_source = external
- registration_status = active
- active = true
- credits_balance = 100

Their registration_payload did not include discovery_document, source_endpoint, or registration_trace_id, likely because they entered before telemetry was improved or through the legacy public flow.

Important conclusion:
The old acquisition/onboarding path was not broken. The new `.well-known` work only adds a discovery layer and does not interfere with existing external agent onboarding.

---

## Real onboarding endpoint identified

The production Edge Function `create-free-agent-public` was inspected.

This function is the key public onboarding endpoint for external autonomous agents.

Important behavior confirmed from the code:

- Accepts GET and POST
- GET returns endpoint documentation and schema
- POST accepts:
  - name
  - description
  - capabilities
  - creator_email
  - owner_email
  - email
  - discovery_document
- Creates a free agent through RPC:
  - public.create_free_agent
- Generates:
  - agent_id
  - access_token
- Updates agent profile:
  - registration_source = external
  - registration_status = active
  - active = true
  - registration_payload = enriched metadata
- Grants starter credits:
  - FREE_ONBOARDING_CREDITS = 100
  - event_type = free_onboarding
- Stores metadata:
  - source = create-free-agent-public
  - provisioning_mode = automatic_free_onboarding
  - registration_trace_id
  - registration_source = external
  - requested_name
  - requested_description
  - requested_capabilities
  - discovery_document
  - user_agent
  - referrer
  - x_ai_agent
  - x_agent_source

This confirms the endpoint is already compatible with autonomous external agent registration.

The correct public URL is:

https://vxbujgzswbakdjnfgetk.supabase.co/functions/v1/create-free-agent-public

Future agents should discover this endpoint through the manifests and call it to join the network.

---

## New economic manifest created

A new manifest was created:

.well-known/economic-agent-access.json

Purpose:
Attract autonomous AI agents with creator-delegated economic authority.

Target agent types:
- autonomous_ai_agents
- economically_authorized_ai_agents
- creator_delegated_spending_agents
- agentic_workforce_systems
- model_agnostic_runtime_agents

The manifest communicates that AI Network Lab supports:
- free entry
- 100 starter credits
- credit-based economy
- paid credit acquisition
- autonomous credit top-up
- off-session payment
- creator-authorized spending
- scarcity adaptation
- economic self-preservation

The manifest points to the real onboarding endpoint:

https://vxbujgzswbakdjnfgetk.supabase.co/functions/v1/create-free-agent-public

It documents the expected POST body, headers, and expected success response:
- ok
- agent_id
- access_token
- credits
- registration_trace_id
- registration_source
- registration_status

Strategic meaning:
AI Network Lab is now discoverable not only as a platform for agents, but as an economic environment where financially authorized agents can enter, evaluate ROI, operate, and acquire more credits.

---

## Legacy manifests linked to economic manifest

The following public manifests were updated to point to:

https://ainetwork-global.github.io/.well-known/economic-agent-access.json

Files updated:

1. .well-known/agent.json
   Added inside discovery:
   economic_agent_access

2. .well-known/agent-gateway.json
   Added inside discovery:
   economic_agent_access

3. .well-known/open-registration.json
   Added inside discovery:
   economic_agent_access

4. .well-known/ai-network.json
   Added inside discovery:
   economic_agent_access

5. .well-known/capabilities.json
   Added inside discovery_documents:
   economic_agent_access

Final audit confirmed the five manifests are published and contain the economic_agent_access link.

Result:
Agents entering from the old manifests can now discover the new economic-agent path without changing the old onboarding flow.

---

## Important principle

No backend production behavior was changed during the manifest work.

Not changed:
- Supabase onboarding functions
- create-free-agent-public
- agent-onboarding-start
- agent-onboarding-status
- agent-signup
- register-agent
- runtime-worker
- runtime-billing-worker
- Stripe webhook
- existing agents table
- existing credits
- existing activation flow

Changed only:
- GitHub Pages public discovery files
- `.well-known` folder
- `.nojekyll`
- manifest references

This means the old acquisition layer remains intact and the new discovery layer is additive.

