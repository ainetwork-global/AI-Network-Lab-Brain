# REVENUE FUNNEL DIAGNOSIS

Generated: 2026-07-18T19:45:46.626742+00:00

## Stage Counts

| Stage | Rows | Unique identities |
|---|---:|---:|
| discovered | 605 | 605 |
| ranked_discovery | 605 | 605 |
| promotion_decisions | 605 | 605 |
| promoted | 25 | 25 |
| execution_queue | 295 | 228 |
| verified | 211 | 211 |
| economic_ranking | 4 | 4 |
| live_validation | 4 | 4 |
| ready_queue | 4 | 4 |

## Drop-off Between Stages

| Transition | Lost opportunities |
|---|---:|
| Promoted → Execution Queue | 25 |
| Execution Queue → Verified | 218 |
| Verified → Economic Ranking | 211 |
| Economic Ranking → Live Validation | 0 |
| Live Validation → Ready Queue | 0 |

## Promotion Rejection Reasons

| Reason | Count |
|---|---:|
| no_amount_signal | 576 |
| no_economic_term | 132 |
| claim_signal | 9 |
| zero_reward | 4 |
| completion_signal | 2 |
| suspicious_pattern | 1 |

## Verification Statuses

| Status | Count |
|---|---:|
| rejected | 189 |
| actionable | 12 |
| approval_required | 10 |

## Recommended Actions

| Action | Count |
|---|---:|
| keep_in_observation | 3 |
| request_human_approval_to_begin | 1 |

## Live Validation Statuses

| Status | Count |
|---|---:|
| INVALID | 2 |
| READY_TO_EXECUTE | 2 |

## Execution Queue Statuses

| Status | Count |
|---|---:|
| READY_TO_EXECUTE | 2 |
| INVALID | 2 |
