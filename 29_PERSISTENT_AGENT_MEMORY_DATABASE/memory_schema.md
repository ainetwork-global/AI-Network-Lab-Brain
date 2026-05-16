# Persistent Agent Memory Database - Schema

Purpose:
Define the logical database schema required for persistent intelligence.

Recommended Supabase tables:

---

## brain_targets

Stores discovered external targets.

Fields:

- id
- name
- url
- source
- creator_or_company
- target_type
- use_case
- economic_capacity_score
- autonomy_score
- conversion_score
- priority_tier
- status
- first_seen_at
- last_seen_at
- notes

---

## brain_signals

Stores external market signals.

Fields:

- id
- source
- signal_type
- url
- summary
- economic_relevance_score
- autonomy_evidence
- related_target_id
- detected_at
- status

---

## brain_outreach

Stores outreach attempts and drafts.

Fields:

- id
- target_id
- channel
- message
- playbook_used
- approval_status
- sent_at
- response_status
- response_summary
- next_action

---

## brain_outcomes

Stores real outcomes.

Fields:

- id
- target_id
- agent_id
- outcome_type
- credits_consumed
- refill_requested
- credits_purchased
- recurring_activity_detected
- observed_at
- learning

---

## brain_hypotheses

Stores strategic assumptions.

Fields:

- id
- hypothesis
- confidence
- evidence_for
- evidence_against
- status
- last_updated_at

---

## brain_decisions

Stores decisions made by the brain.

Fields:

- id
- decision
- reason
- expected_outcome
- actual_outcome
- confidence
- created_at
- reviewed_at
