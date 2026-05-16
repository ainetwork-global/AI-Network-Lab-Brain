# Live Agent Scout Runtime - Workflow

Purpose:
Define how the scout runtime should operate.

Runtime flow:

1. Select source

Choose source based on priority:
- AI workforce products
- GitHub
- X / Twitter
- MCP ecosystem
- agent marketplaces

2. Run query

Use queries from:
16_AGENT_ACQUISITION_ENGINE/search_queries.md

3. Extract candidates

For each candidate, extract:
- name
- URL
- source
- creator/company
- agent type
- use case
- evidence of autonomy
- evidence of economic purpose
- possible budget source

4. Score candidate

Use:
24_ECONOMIC_BEHAVIOR_PREDICTION_ENGINE/prediction_model.md

5. Store memory

Save target into:
29_PERSISTENT_AGENT_MEMORY_DATABASE

6. Recommend action

Possible outputs:
- ignore
- monitor
- score deeper
- prepare outreach
- add to high-priority list

Rule:
No outreach should happen directly from scout runtime without approval.
