# Autonomous Scheduler - Safety

Purpose:
Prevent unsafe scheduled autonomy.

Rules:

1. Scheduled tasks may read, score, log, and recommend.

2. Scheduled tasks may not send external messages without approval.

3. Scheduled tasks may not spend money.

4. Scheduled tasks may not modify production systems without explicit approval.

5. Scheduled tasks must avoid repeated outreach.

6. Scheduled tasks must preserve audit logs.

7. Scheduled tasks must downgrade stale or low-value targets.

8. Scheduled tasks must escalate high-value opportunities for review.

Default mode:
Daily advisory scheduler.

Next safe mode:
Daily assisted execution scheduler.

Forbidden:
Mass automated outreach.
