# Agent Intelligence Brain - Prioritization Model

Purpose:
Rank targets by expected strategic and economic value.

Score each target from 0 to 100.

Scoring model:

## Economic capacity - 25 points
- clear company/founder/operator: +10
- likely budget: +10
- paid tools/API usage: +5

## Agent autonomy - 20 points
- autonomous workflow: +10
- tool/API execution: +5
- recurring operation: +5

## ROI potential - 20 points
- measurable output: +10
- direct business value: +5
- likely improvement from credits: +5

## Strategic relevance - 15 points
- aligned with agent economy: +5
- aligned with multi-agent systems: +5
- aligned with economically constrained intelligence: +5

## Network effect - 10 points
- public audience: +5
- can influence other agent creators: +5

## Conversion confidence - 10 points
- public interest in agent monetization: +5
- direct fit with AI Network Lab docs: +5

Priority bands:

80-100:
Immediate priority.

60-79:
High-quality target.

40-59:
Monitor.

0-39:
Low priority.

Rule:
Do not pursue low-score targets aggressively.
