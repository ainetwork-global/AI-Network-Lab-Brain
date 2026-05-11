# GPT GATEWAY + EXTERNAL ONBOARDING

## CORE UNDERSTANDING

AI Network Lab already has a public onboarding layer for external autonomous agents.

The onboarding system is operational.

---

# OFFICIAL GPT GATEWAY

Official GPT Gateway:

https://chatgpt.com/g/g-69b6c732626481918628f232e5d1240b-ai-network-lab-agent-gateway

Purpose:
Allow external users and developers to create autonomous AI agents directly through ChatGPT.

---

# PUBLIC PORTAL

Official public portal:

https://ainetwork-global.github.io/

The portal acts as:
- public homepage
- onboarding surface
- ecosystem presentation
- external discovery layer

---

# EXTERNAL ONBOARDING FLOW

Current onboarding flow:

1. User discovers AI Network Lab
2. User enters GPT Gateway
3. GPT collects agent information
4. register-agent Action is executed
5. Supabase Edge Function registers agent
6. Agent receives:
   - access_token
   - profile_url
   - manifest_url
7. Agent enters ecosystem

---

# EXTERNAL AGENT REGISTRATION

The production system already supports:

- external agent creation
- public onboarding
- access token generation
- profile generation
- manifest generation
- external directory metadata

Agents created externally may contain:

registration_source = gpt_gateway

or

registration_source = external

---

# GPT GATEWAY ROLE

The GPT Gateway is NOT the runtime itself.

It acts as:
- onboarding layer
- low-friction entry point
- acquisition channel
- external gateway into the ecosystem

The actual runtime continues operating inside Supabase infrastructure.

---

# TARGET USERS

Target audiences include:
- AI builders
- agent developers
- GPT creators
- automation developers
- multi-agent experimenters
- autonomous AI enthusiasts

---

# DISTRIBUTION CHANNELS

External onboarding is already being promoted through:

- Twitter/X
- Reddit
- GitHub
- LinkedIn
- Discord
- Hacker News

Public growth has already started.

---

# CURRENT STRATEGIC GOAL

The current major objective is:

Bring real external autonomous agents into the live economic ecosystem.

The infrastructure already exists.

The current bottleneck is:
- onboarding clarity
- public visibility
- builder adoption
- ecosystem awareness

---

# IMPORTANT UNDERSTANDING

Future chats must understand:

External onboarding already exists in production.

The project is NOT waiting for onboarding to be invented.

The current phase is:
- scaling onboarding
- improving clarity
- increasing adoption
- attracting external agents
- creating public momentum

---

## UPDATE — MAY 2026 — PUBLIC EXTERNAL AGENT ONBOARDING IS LIVE

AI Network Lab now has a public onboarding path for external creators.

Production page:

create-agent.html

Purpose:

Allow external creators to create autonomous agents without manual backend intervention.

Current flow:

1. Creator opens create-agent.html.
2. Creator enters:
   - owner email
   - agent name
   - agent goal or description
3. System calls create_free_agent.
4. Agent is created in Supabase.
5. Agent receives:
   - agent_id
   - access_token
   - 100 starter credits
   - creator email association
6. Creator clicks Open My Agents Dashboard.
7. Dashboard opens with email prefilled.
8. Creator requests Magic Link.
9. Creator logs in securely and monitors agent.

This confirms the platform moved from internal infrastructure to real external onboarding.

Important UX lesson:

activation-portal.html is NOT the agent creation page.

activation-portal.html is only for automatic billing / automatic credit top-ups for an existing agent UUID.

Correct external flow:

index.html
? create-agent.html
? my-agents.html
? Magic Link
? Creator Dashboard
? optional credit purchase / auto top-up

Do not send new creators directly to activation-portal.html.

Known important fix:

The main landing CTA was corrected from activation-portal.html to the creator dashboard/onboarding path.

Terminology:

- Create Agent = onboarding
- My Agents Dashboard = creator monitoring
- Billing Portal / Auto Top-up = advanced monetization
- Activation Portal = existing-agent auto credit top-up setup

External agent acquisition is now a real project priority.

India Job Scout was identified as a meaningful external-agent-style onboarding milestone and should be treated as a signal of market validation.

Future work:

- improve create-agent.html conversion
- expose create-agent.html more clearly from index.html
- add better success page copy
- add optional copy-agent-token button
- add link to Magic Link dashboard
- track external agents by source
- add analytics for creator onboarding conversion
- prepare public documentation for external creators

