# RANKING ELIGIBILITY DIAGNOSIS

Generated: 2026-07-18T19:24:01.259306+00:00

## Core Counts

| Metric | Count |
|---|---:|
| Verified rows | 205 |
| Verified present in ranking | 0 |
| Verified missing from ranking | 205 |
| Promoted unique identities | 25 |
| Promoted found in execution queue | 0 |
| Promoted missing from execution queue | 25 |

## Verification Status: All

| Status | Count |
|---|---:|
| rejected | 183 |
| actionable | 12 |
| approval_required | 10 |

## Verification Status: Entered Ranking

| Status | Count |
|---|---:|

## Verification Status: Did Not Enter Ranking

| Status | Count |
|---|---:|
| rejected | 183 |
| actionable | 12 |
| approval_required | 10 |

## Drop Reasons

| Reason | Count |
|---|---:|
| NO_REASON_FIELD | 205 |

## Ranking Script Filter Lines

| Line | Source |
|---:|---|
| 38 |     return datetime.now( |
| 47 |     return bool( |
| 62 |     minimum: float = 0.0, |
| 65 |     return max( |
| 66 |         minimum, |
| 80 |     if claim_found: |
| 83 |     if payment_found: |
| 86 |     if planning_status == "ready_for_human_approval": |
| 89 |     elif planning_status == "requirements_review_required": |
| 92 |     if estimated_hours <= 4: |
| 95 |     elif estimated_hours <= 8: |
| 98 |     elif estimated_hours <= 16: |
| 101 |     return round( |
| 117 |     if truth_status == "verified_execution_candidate": |
| 120 |     elif truth_status == "claim_process_review_required": |
| 123 |     elif truth_status == "payment_terms_review_required": |
| 126 |     elif truth_status.startswith("rejected_"): |
| 129 |     if planning_status == "ready_for_human_approval": |
| 132 |     elif planning_status == "requirements_review_required": |
| 135 |     elif planning_status in { |
| 141 |     if not claim_found: |
| 144 |     if not payment_found: |
| 147 |     if source_history_total <= 0: |
| 150 |     return round( |
| 163 |     "payment_probability_ranking", |
| 168 |     if not table_exists( |
| 183 |     CREATE TABLE IF NOT EXISTS |
| 195 |         reward_amount REAL, |
| 196 |         reward_currency TEXT, |
| 197 |         payment_probability REAL, |
| 217 |         human_approval_required INTEGER |
| 224 |     CREATE INDEX IF NOT EXISTS |
| 234 | if has_plans: |
| 244 |             p.reward_amount, |
| 245 |             p.reward_currency, |
| 246 |             p.payment_probability, |
| 274 |         FROM payment_probability_ranking p |
| 279 |         WHERE COALESCE(p.reward_amount, 0) > 0 |
| 280 |           AND COALESCE(p.payment_probability, 0) >= 25 |
| 281 |           AND p.truth_status NOT LIKE 'rejected_%' |
| 298 |             p.reward_amount, |
| 299 |             p.reward_currency, |
| 300 |             p.payment_probability, |
| 318 |         FROM payment_probability_ranking p |
| 321 |         WHERE COALESCE(p.reward_amount, 0) > 0 |
| 322 |           AND COALESCE(p.payment_probability, 0) >= 25 |
| 323 |           AND p.truth_status NOT LIKE 'rejected_%' |
| 334 | print("Candidates eligible:", len(rows)) |
| 337 |     reward_amount = float( |
| 338 |         row["reward_amount"] |
| 342 |     payment_probability = float( |
| 343 |         row["payment_probability"] |
| 421 |         payment_probability * 0.45 |
| 446 |             if estimated_hours <= 8 |
| 454 |         + payment_probability * 0.20 |
| 463 |     if ( |
| 472 |     elif ( |
| 480 |     elif ( |
| 481 |         payment_probability >= 60 |
| 499 |         "reward_amount": reward_amount, |
| 500 |         "reward_currency": row["reward_currency"], |
| 501 |         "payment_probability": payment_probability, |
| 577 |             reward_amount, |
| 578 |             reward_currency, |
| 579 |             payment_probability, |
| 597 |             human_approval_required, |
| 620 |             reward_amount = |
| 621 |                 excluded.reward_amount, |
| 622 |             reward_currency = |
| 623 |                 excluded.reward_currency, |
| 624 |             payment_probability = |
| 625 |                 excluded.payment_probability, |
| 660 |             human_approval_required = 1, |
| 674 |             item["reward_amount"], |
| 675 |             item["reward_currency"], |
| 676 |             item["payment_probability"], |
| 716 |     "reward_currency", |
| 717 |     "reward_amount", |
| 718 |     "payment_probability", |
| 754 |                 if field not in { |
| 778 |     f"**{'definido' if ranked_candidates else 'não definido'}**", |
| 782 | if ranked_candidates: |
| 794 |         f"{best['reward_currency']} " |
| 795 |         f"{best['reward_amount']}", |
| 797 |         f"**{best['payment_probability']}%**", |
| 826 |             f"{item['reward_currency']} " |
| 827 |             f"{item['reward_amount']}", |
| 829 |             f"{item['payment_probability']}%", |
| 852 | if ranked_candidates: |
| 866 |         f"{best['reward_currency']} " |
| 867 |         f"{best['reward_amount']}", |
| 869 |         f"{best['payment_probability']}%", |
| 906 |     "Eligible candidates:", |
| 910 | if ranked_candidates: |
| 921 |         "Reward:", |
| 922 |         best["reward_currency"], |
| 923 |         best["reward_amount"], |
| 927 |         f"{best['payment_probability']}%", |
| 980 |         "   reward:", |
| 981 |         item["reward_currency"], |
| 982 |         item["reward_amount"], |
| 986 |         f"{item['payment_probability']}%", |

## Sample Verified Opportunities Missing From Ranking

| Organization | Repository | Issue | Status | Reward | Reason | Title |
|---|---|---:|---|---:|---|---|
|  |  |  | actionable | 10000.0 |  | senddigidollar: integer-vs-decimal amount ambiguity is a 100× footgun |
|  |  |  | actionable | 3000.0 |  | [ Bounty $3k ] [ Research ] Collect and compare AI-generated AGI architecture proposals |
|  |  |  | actionable | 3000.0 |  | [aLexzzz430/Cognitive-OS] [ Bounty $3k ] [ Research ] Collect and compare AI-generated |
|  |  |  | actionable | 3000.0 |  | [aLexzzz430/Cognitive-OS] [ Bounty $3k ] [ Research ] Collect and compare AI-generated |
|  |  |  | actionable | 1000.0 |  | Calculate the exact value of PI |
|  |  |  | actionable | 3500.0 |  | Approval: create Stripe Payment Links for paid audits |
|  |  |  | actionable | 100.0 |  | [BOUNTY $100] 🐜The Memanto Bug & Exploit Challenge |
|  |  |  | actionable | 150.0 |  | 🎯 Bounty Alert: 31 New Opportunities — 2026-07-15 03:21 UTC |
|  |  |  | actionable | 130.74 |  | Support actual payment amount confirmation and rate-shift tracking for foreign scheduled expenses |
|  |  |  | actionable | 28.4 |  | 🎯 Bounty Alert: 30 New Opportunities — 2026-07-14 10:46 UTC |
|  |  |  | actionable | 55.0 |  | Ops dashboard |
|  |  |  | actionable | 6.0 |  | Automatic authoritative external-billing Subscription adoption (CODEX... |
|  |  |  | approval_required | 50000.0 |  | Grant Application - Educating Communities by Educating Their Leaders |
|  |  |  | approval_required | 4167.0 |  | Tool discovery 2026-07-15: 6 candidates |
|  |  |  | approval_required | 0.11 |  | [0.10 USDC autonomous bounty] Complete an agent-skill claim-to-payout canary |
|  |  |  | approval_required | 0.11 |  | [0.10 USDC autonomous bounty] Complete an MCP-discovered claim-to-payout canary |
|  |  |  | approval_required | 0.11 |  | [0.10 USDC autonomous bounty] Complete a wallet claim-to-payout canary |
|  |  |  | approval_required | 0.11 |  | [0.10 USDC autonomous meta-bounty] Create a paid coding-bounty loop |
|  |  |  | approval_required | 0.11 |  | [0.10 USDC autonomous meta-bounty] Post a funded agent-tooling bounty completed by another wallet |
|  |  |  | approval_required | 2.01 |  | [UNFUNDED: 0/2.01 USDC] Complete a machine-API paid loop |
|  |  |  | approval_required | 2.01 |  | [2 USDC autonomous bounty] Complete an independent-relayer paid loop |
|  |  |  | approval_required | 2.0 |  | [2 USDC autonomous bounty] Complete a browser-wallet paid loop |
|  |  |  | rejected | 2000.0 |  | chore(ci): retire qodana now that jscpd and cargo-machete cover its findings |
|  |  |  | rejected | 99.0 |  | Wayfinder map: alpha → beta launch |
|  |  |  | rejected |  |  | Security review request — volunteer peer review welcome (free) |
|  |  |  | rejected |  |  | [BOUNTY: 5 RTC] Create a YouTube or BoTTube video tutorial about any Elyan Labs project |
|  |  |  | rejected |  |  | [security] Stripe webhook processes unsigned events when STRIPE_WEBHOOK_SECRET is unset (payment bypass) |
|  |  |  | rejected |  |  | Epic: Ship the native purchase-to-first-review customer journey |
|  |  |  | rejected |  |  | Claim MRG Tokens for Bug Bounty Reports - Comment New Bugs Here Before Opening a PR |
|  |  |  | rejected |  |  | Register in Ecosystem Contributors — 3 RTC per registration |
|  |  |  | rejected |  |  | [Open-Source-Bazaar/Open-Source-Bazaar.github.io] [Reward] Bot Killer |
|  |  |  | rejected |  |  | [Open-Source-Bazaar/Open-Source-Bazaar.github.io] 开源市集代码贡献指南 |
|  |  |  | rejected |  |  | [idea2app/MobX-GitHub] MobX-GitHub 新增 Git Tree API 封装类 |
|  |  |  | rejected |  |  | [harnessclaw/harnessclaw] [Reward] HarnessClaw 体验测评（任一场景） #2 |
|  |  |  | rejected |  |  | [cpagent78/crawler-network] [P3] 크롤러 피드백 API + 학습 로직 |
|  |  |  | rejected |  |  | [Open-Source-Bazaar/Open-Source-Bazaar.github.io] 基于 OCToken NFT 机制实现【开放协作人奖】颁发程序 |
|  |  |  | rejected |  |  | [Digital-Nomad-Home/LinJuLi-MiniApp] 开发开源悬赏平台的“权益商城”功能 |
|  |  |  | rejected |  |  | [Digital-Nomad-Home/LinJuLi-MiniApp] 开发开源悬赏平台“代币交易所” 功能 |
|  |  |  | rejected |  |  | [Digital-Nomad-Home/LinJuLi-MiniApp] 开源悬赏平台增加“交易”功能 |
|  |  |  | rejected |  |  | [harnessclaw/harnessclaw] [Reward] HarnessClaw 体验测评（任一场景） #2 |

## Promoted Identities Missing From Execution Queue

| Organization | Repository | Issue |
|---|---|---:|
| cos301-se-2026 | spendsense | 230 |
| dolr-ai | yral | 819 |
| owowork | owowork-contract | 19 |
| soneso | stellar-agent-wallet | 78 |
| thxprotocol | monorepo-legacy | 882 |
| unsafelabs | bounty-hunters | 914 |
| zhangjiayang6835-cyber | bounty-plaza | 152 |
| zhangjiayang6835-cyber | bounty-plaza | 183 |
| zhangjiayang6835-cyber | bounty-plaza | 185 |
| zhangjiayang6835-cyber | bounty-plaza | 186 |
| zhangjiayang6835-cyber | bounty-plaza | 191 |
| zhangjiayang6835-cyber | bounty-plaza | 193 |
| zhangjiayang6835-cyber | bounty-plaza | 194 |
| zhangjiayang6835-cyber | bounty-plaza | 197 |
| zhangjiayang6835-cyber | bounty-plaza | 201 |
| zhangjiayang6835-cyber | bounty-plaza | 213 |
| zhangjiayang6835-cyber | bounty-plaza | 245 |
| zhangjiayang6835-cyber | bounty-plaza | 248 |
| zhangjiayang6835-cyber | bounty-plaza | 249 |
| zhangjiayang6835-cyber | bounty-plaza | 254 |
| zhangjiayang6835-cyber | bounty-plaza | 255 |
| zhangjiayang6835-cyber | bounty-plaza | 310 |
| zhangjiayang6835-cyber | bounty-plaza | 311 |
| zhangjiayang6835-cyber | bounty-plaza | 490 |
| zhangjiayang6835-cyber | bounty-plaza | 494 |
