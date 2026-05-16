# Persistent Agent Memory Database - Status

Current status:
DESIGN COMPLETE.

Operational status:
NOT YET DEPLOYED TO SUPABASE.

Next required implementation:

1. Create Supabase tables:
- brain_targets
- brain_signals
- brain_outreach
- brain_outcomes
- brain_hypotheses
- brain_decisions

2. Add RLS policies.

3. Create service-role-only Edge Functions for:
- log signal
- score target
- update target status
- record outcome
- update hypothesis

4. Connect scheduler.

5. Connect scout runtime.

Default rule:
Until database exists, memory is stored in markdown logs.

Next layer:
Autonomous Scheduler.
