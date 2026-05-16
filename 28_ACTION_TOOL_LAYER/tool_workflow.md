# Action Tool Layer - Tool Workflow

Purpose:
Define how tools should work together.

Workflow:

1. Signal scanner finds possible target.

2. GitHub / web / social scout enriches target.

3. Scoring engine evaluates economic relevance.

4. Prediction engine estimates refill probability.

5. Conversion engine selects playbook.

6. Outreach composer drafts message.

7. Human approves or rejects.

8. Memory logger records outcome.

9. Learning layer updates strategy.

Rule:
Every external action must pass through scoring and safety checks.

Default path:

Discover
→ Enrich
→ Score
→ Predict
→ Draft
→ Approve
→ Act
→ Learn

Never skip scoring.
