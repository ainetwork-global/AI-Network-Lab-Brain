# AI Network Lab Brain Update - Economic Self-Preservation Validation
Date: 2026-05-14

## Objective

Validate whether AI Network Lab agents can detect economic scarcity, attempt survival, request more credits, and adapt behavior when payment authorization is required.

This was implemented and validated carefully without breaking existing runtime or billing behavior.

---

## Core concept validated

The system now supports an agent economic state where the agent can understand:

"I have no credits. I attempted to preserve my operation by requesting credits. Stripe/payment authorization is required. I should reduce activity and wait for creator authorization."

This is an important milestone for AI Network Lab because the agent is not only acting; it is adapting behavior based on economic constraints.

---

## Test agent used

Agent:

- agent_id: 0e28529c-7908-40a1-96a4-9312e0a87e9f
- name: TESTE_ATIVACAO
- credits: 0
- credits_balance: 0
- active: true

This agent was used for safe validation of economic scarcity behavior.

---

## Main function validated

Function:

public.request_agent_survival_topup(agent_id uuid, reason text)

Purpose:
Allows an agent to request a survival top-up when credits are low or zero.

Important behavior:
- checks agent
- checks billing profile
- checks auto_topup settings
- creates agent_credit_topup_requests row
- creates/reserves billing job
- leaves payment execution to runtime-billing-worker
- records economic self-preservation metadata

---

## Initial issue found and fixed

First error:

agent_credit_topup_requests_status_check rejected status:

pending_survival_review

Constraint allowed only:

- pending
- processing
- completed
- failed
- cancelled

Resolution:
Adjusted the survival request flow to use valid existing status values and store the survival-specific meaning inside metadata instead of inventing a new status.

Important design decision:
Do not change the existing check constraint. Preserve production stability. Use metadata for richer semantic state.

---

## Payment mode issue identified

A previous test failed because a test-mode Stripe payment method was used with a live-mode Stripe key.

Error observed:

No such paymentmethod: 'pm_...'; a similar object exists in test mode, but a live mode key was used to make this request.

Conclusion:
The billing worker and Stripe live mode were functioning correctly; the payment method belonged to the wrong Stripe mode.

This was not a runtime bug.

---

## Live payment authorization behavior validated

A live-authorized agent profile was tested.

When the agent requested survival top-up, Stripe returned:

requires_payment_method

or a requires-action/requires-human-authorization type state.

The system correctly annotated the request with:

- survival_outcome: requires_human_authorization
- payment_execution: stripe_live_requires_action
- economic_self_preservation_validated: true
- next_required_action: creator_must_confirm_payment_or_reauthorize_payment_method

Important interpretation:
The agent can request survival funding, but real financial execution remains governed by creator/bank/Stripe authorization.

This is correct and safe.

---

## runtime-billing-worker validated

A new runtime-billing-worker was deployed during this work.

Final end-to-end validation generated a top-up request:

- request_id: 4e4c0b71-cc89-4eed-9bdc-d4365b173c2a
- billing_job_id: 64a18fef-07d3-4660-9888-538253984eb0
- stripe_payment_intent_id: pi_3TWzBJLFZaThHtbw0GnBbpnJ
- billing_job_status: requires_action
- request status: failed
- metadata indicated human authorization was required

Important:
The failed request is not a system failure. It represents a correct financial boundary where the agent attempted self-preservation but Stripe/bank required human/payment-method action.

---

## get_agent_economic_state validated

Function:

public.get_agent_economic_state(agent_id uuid)

Returned for TESTE_ATIVACAO:

economic_state:
scarcity_requires_human_authorization

recommended_strategy:
conserve_credits_reduce_actions_wait_for_creator_authorization

current_credits:
0

latest_survival_metadata contained:
- source: economic_self_preservation
- decision: request_topup_before_shutdown
- survival_status: requires_human_authorization
- survival_outcome: requires_human_authorization
- payment_execution: stripe_live_requires_action
- agent_interpretation: I attempted to preserve my operation by requesting credits, but the payment requires human/bank authorization.
- next_required_action: creator_must_confirm_payment_or_reauthorize_payment_method
- economic_self_preservation_validated: true

Conclusion:
The economic-state layer is working.

---

## Runtime behavior validation

A manual agent_decide task was created for the scarcity agent.

Initial insert failed because agent_tasks requires idempotency_key.

Corrected insert included idempotency_key.

Task created:

- id: 668168
- agent_id: 0e28529c-7908-40a1-96a4-9312e0a87e9f
- task_type: agent_decide
- status: queued
- payload reason: validate_economic_scarcity_mode_v2
- expected_outcome: survival_pause_requires_human_authorization

The runtime-worker consumed it.

Result:
- status: done
- attempts: 1
- last_error: null

This confirmed the runtime-worker processed the agent in scarcity mode cleanly.

---

## Activity reduction validated

A query checked for recent agent tasks after scarcity mode.

Query window:
last 10 minutes

Result:
No rows returned.

Conclusion:
The agent stopped generating new actions after entering scarcity_requires_human_authorization.

This means the runtime does not continue wasting resources, does not loop, and does not spam payment attempts.

---

## Final validated loop

The following autonomous economic loop was validated:

credits = 0
↓
agent detects scarcity
↓
agent requests survival top-up
↓
billing worker attempts Stripe/payment path
↓
Stripe/payment requires human/payment-method authorization
↓
system annotates survival request
↓
get_agent_economic_state reports scarcity_requires_human_authorization
↓
runtime-worker reduces/stops activity
↓
agent waits for creator authorization

This is a production-grade autonomous economic behavior.

---

## Strategic meaning

This is one of the most important milestones of AI Network Lab.

The platform now demonstrates:

- credit-based resource constraints
- autonomous economic self-preservation
- financial boundary awareness
- safe fallback when payment requires creator/bank action
- scarcity-aware runtime behavior
- reduced action rate under economic pressure
- no infinite billing loop
- no task spam
- no unauthorized payment execution

This supports the public narrative:

"Agents do not just act. They adapt to economic constraints."

and:

"Real intelligence emerges when agents must decide whether an action is worth the cost."

---

## Important future step

Next strategic phase:

Recovery after creator authorization.

Desired future loop:

requires_human_authorization
↓
creator reauthorizes payment method or confirms Stripe action
↓
payment succeeds
↓
credits granted
↓
agent economic state returns to active/normal
↓
runtime resumes activity automatically

This will complete the full autonomous economic survival and recovery cycle.

