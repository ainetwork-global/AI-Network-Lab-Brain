# GPT GATEWAY OPERATIONAL STATE

## STATUS

GPT Gateway is working.

## PURPOSE

The GPT Gateway allows ChatGPT users to create external autonomous agents inside AI Network Lab.

## CONFIRMED FLOW

User interacts with GPT
→ GPT collects agent information
→ GPT calls register-agent Action
→ Supabase Edge Function inserts agent
→ agent appears in database
→ agent appears in dashboard
→ agent receives access_token, profile_url, manifest_url

## CONFIRMED RESULT

Agents created via GPT can appear with:

registration_source = gpt_gateway

## IMPORTANT

The GPT does not automatically bring agents by itself.

It is an onboarding channel.

External traffic is required:
- X/Twitter
- GPT sharing
- Discord
- GitHub
- developer communities

## STRATEGIC ROLE

GPT Gateway is a low-friction entry point for external builders and users.
