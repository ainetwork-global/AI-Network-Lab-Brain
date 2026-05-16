# Opportunity Ranking Runtime - Workflow

Purpose:
Define how ranking should happen after scout discovery.

Workflow:

1. Receive candidate from scout runtime.

2. Enrich candidate:
- company/founder context
- agent type
- use case
- budget likelihood
- autonomy evidence
- public activity
- technical maturity

3. Score candidate using:
- prediction model
- conversion signals
- revenue signals
- market dominance priority

4. Assign priority band:
- Critical
- High
- Monitor
- Low

5. Recommend action:
- immediate outreach draft
- monitor
- add to watchlist
- ignore

6. Store result in persistent memory.

7. Re-rank when new evidence appears.

Rule:
Ranking must be dynamic.

Evidence can upgrade or downgrade any target.
