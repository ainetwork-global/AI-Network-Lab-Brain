# Live Mode Activation Plan - Required Components

Required before real live operation:

1. Supabase brain memory tables

Tables:
- brain_targets
- brain_signals
- brain_scores
- brain_outreach
- brain_outcomes
- brain_hypotheses
- brain_runtime_logs

2. Edge Function runtime

Function:
brain-orchestrator

Purpose:
Run the brain loop.

3. Scheduler

First cadence:
Daily.

4. Web/GitHub signal scanner

Purpose:
Find external agents and ecosystems.

5. Scoring runtime

Purpose:
Rank targets economically.

6. Approval queue

Purpose:
Human approves external action.

7. Runtime logs

Purpose:
Audit every decision.
