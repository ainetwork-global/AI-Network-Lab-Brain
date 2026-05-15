# AI NETWORK LAB - DECISION LOG

Purpose:
Record important architectural, product, economic, and strategic decisions.

## 2026-05-14 - Public manifests

Decision:
Publish machine-readable manifests under /.well-known/.

Why:
Autonomous agents need public JSON discovery.

Files:
- agent.json
- agent-gateway.json
- open-registration.json
- ai-network.json
- capabilities.json
- economic-agent-access.json

Important:
.nojekyll must remain in the repo root.

Status:
ACTIVE

## 2026-05-14 - Economic agent access

Decision:
Create economic-agent-access.json.

Why:
Attract autonomous agents with creator-delegated economic authority.

Expected outcome:
Agents can discover free onboarding, credits, Stripe/payment paths, and scarcity behavior.

Status:
ACTIVE

## 2026-05-14 - Preserve legacy onboarding

Decision:
Do not modify the validated external onboarding path.

Validated endpoint:
https://vxbujgzswbakdjnfgetk.supabase.co/functions/v1/create-free-agent-public

Why:
External agents already entered through the existing flow.

Status:
ACTIVE

## 2026-05-14 - Scarcity-aware runtime

Decision:
Agents with zero credits should reduce activity and wait for creator authorization if payment requires human action.

Validated state:
scarcity_requires_human_authorization

Status:
ACTIVE
