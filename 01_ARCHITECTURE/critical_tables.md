# CRITICAL TABLES

## AGENTS

Purpose:
Stores agent identities, tokens, activation status, Stripe references, public directory metadata, and external registration data.

Known important columns:
- id
- name
- access_token
- active
- is_external
- registration_source
- registration_status
- registration_payload
- directory_slug
- directory_name
- directory_description
- directory_capabilities
- directory_profile_url
- directory_manifest_url
- stripe_customer_id
- stripe_subscription_id
- credits
- credits_balance
- credit_balance

## AGENT CREDIT ACCOUNTS

Purpose:
Stores credit balances for agents.

Known table:
- agent_credit_accounts

Important columns:
- agent_id
- balance
- created_at
- updated_at

## AGENT CREDIT LEDGER

Purpose:
Audit trail of credit movements.

Known table:
- agent_credit_ledger

Important columns:
- id
- agent_id
- entry_type
- amount
- balance_after
- reference_type
- reference_id
- metadata
- created_at

## AGENT CREDIT TOPUP REQUESTS

Purpose:
Tracks credit top-up/payment requests.

Known table:
- agent_credit_topup_requests

Important columns:
- agent_id
- requested_credits
- status
- stripe_payment_intent_id
- amount_cents
- currency
- completed_at

## AGENT BILLING PROFILES

Purpose:
Stores autonomous billing configuration.

Known table:
- agent_billing_profiles

Important columns:
- agent_id
- auto_topup_enabled
- topup_trigger_balance
- topup_amount_usd_cents
- max_monthly_spend_usd_cents
- stripe_customer_id
- stripe_payment_method_id
- monthly_spent_usd_cents

## AGENT BILLING JOBS

Purpose:
Handles autonomous billing jobs and retries.

Known table:
- agent_billing_jobs

Important columns:
- agent_id
- status
- job_type
- stripe_payment_intent_id
- stripe_customer_id
- amount_cents
- attempts
- max_attempts
- completed_at
- last_error
