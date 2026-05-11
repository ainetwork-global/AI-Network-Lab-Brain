# SUPABASE OPERATIONAL STATE

## STATUS

Supabase is the primary backend infrastructure for AI Network Lab.

## CORE RESPONSIBILITIES

Supabase handles:
- PostgreSQL database
- Edge Functions
- RPC functions
- agent registration
- runtime workers
- task queues
- credit economy
- public APIs
- Stripe webhook processing

## IMPORTANT

Supabase is the operational core of the project.

Do not replace Supabase.
Do not redesign the backend from scratch.
Do not suggest migrating to another backend unless explicitly requested.

## CURRENT PRODUCTION CONTEXT

AI Network Lab already runs in production using Supabase.

The project is not in prototype-only mode.

Future chats must assume:
- database exists
- Edge Functions exist
- Stripe integration exists
- runtime architecture exists
- credit economy exists
- GPT Gateway registration exists
