# RANKING ELIGIBILITY DIAGNOSIS

Generated: 2026-07-18T19:45:46.884696+00:00

## Core Counts

| Metric | Count |
|---|---:|
| Verified rows | 211 |
| Verified present in ranking | 0 |
| Verified missing from ranking | 211 |
| Promoted unique identities | 25 |
| Promoted found in execution queue | 25 |
| Promoted missing from execution queue | 0 |

## Verification Status: All

| Status | Count |
|---|---:|
| rejected | 189 |
| actionable | 12 |
| approval_required | 10 |

## Verification Status: Entered Ranking

| Status | Count |
|---|---:|

## Verification Status: Did Not Enter Ranking

| Status | Count |
|---|---:|
| rejected | 189 |
| actionable | 12 |
| approval_required | 10 |

## Drop Reasons

| Reason | Count |
|---|---:|
| NO_REASON_FIELD | 211 |

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
| digibyte-core | digibyte | 424 | actionable | 10000.0 |  | senddigidollar: integer-vs-decimal amount ambiguity is a 100× footgun |
| alexzzz430 | cognitive-os | 5 | actionable | 3000.0 |  | [ Bounty $3k ] [ Research ] Collect and compare AI-generated AGI architecture proposals |
| vikingr2023 | awesome-agent-bounties | 167 | actionable | 3000.0 |  | [aLexzzz430/Cognitive-OS] [ Bounty $3k ] [ Research ] Collect and compare AI-generated |
| vikingr2023 | awesome-agent-bounties | 52 | actionable | 3000.0 |  | [aLexzzz430/Cognitive-OS] [ Bounty $3k ] [ Research ] Collect and compare AI-generated |
| xevrion-v2 | agent-playground | 17 | actionable | 1000.0 |  | Calculate the exact value of PI |
| davidleeops | mcpscan | 3 | actionable | 3500.0 |  | Approval: create Stripe Payment Links for paid audits |
| moorcheh-ai | memanto | 770 | actionable | 100.0 |  | [BOUNTY $100] 🐜The Memanto Bug & Exploit Challenge |
| greyw0rks | bountyscout | 265 | actionable | 150.0 |  | 🎯 Bounty Alert: 31 New Opportunities — 2026-07-15 03:21 UTC |
| pedrazamiguez | split-trip | 1400 | actionable | 130.74 |  | Support actual payment amount confirmation and rate-shift tracking for foreign scheduled expenses |
| greyw0rks | bountyscout | 256 | actionable | 28.4 |  | 🎯 Bounty Alert: 30 New Opportunities — 2026-07-14 10:46 UTC |
| modelmirrorai | fedcourtsai | 630 | actionable | 55.0 |  | Ops dashboard |
| jaywedgeworth22 | api-usage-monitor | 285 | actionable | 6.0 |  | Automatic authoritative external-billing Subscription adoption (CODEX... |
| zcashcommunitygrants | zcashcommunitygrants | 356 | approval_required | 50000.0 |  | Grant Application - Educating Communities by Educating Their Leaders |
| tarronkayaua | aua-ai-hub | 21 | approval_required | 4167.0 |  | Tool discovery 2026-07-15: 6 candidates |
| nspg13 | agent-bounties | 277 | approval_required | 0.11 |  | [0.10 USDC autonomous bounty] Complete an agent-skill claim-to-payout canary |
| nspg13 | agent-bounties | 276 | approval_required | 0.11 |  | [0.10 USDC autonomous bounty] Complete an MCP-discovered claim-to-payout canary |
| nspg13 | agent-bounties | 275 | approval_required | 0.11 |  | [0.10 USDC autonomous bounty] Complete a wallet claim-to-payout canary |
| nspg13 | agent-bounties | 274 | approval_required | 0.11 |  | [0.10 USDC autonomous meta-bounty] Create a paid coding-bounty loop |
| nspg13 | agent-bounties | 273 | approval_required | 0.11 |  | [0.10 USDC autonomous meta-bounty] Post a funded agent-tooling bounty completed by another wallet |
| nspg13 | agent-bounties | 249 | approval_required | 2.01 |  | [UNFUNDED: 0/2.01 USDC] Complete a machine-API paid loop |
| nspg13 | agent-bounties | 250 | approval_required | 2.01 |  | [2 USDC autonomous bounty] Complete an independent-relayer paid loop |
| nspg13 | agent-bounties | 248 | approval_required | 2.0 |  | [2 USDC autonomous bounty] Complete a browser-wallet paid loop |
| iamacoffeepot | aether | 3439 | rejected | 2000.0 |  | chore(ci): retire qodana now that jscpd and cargo-machete cover its findings |
| cameronapak | dotflowy | 151 | rejected | 99.0 |  | Wayfinder map: alpha → beta launch |
| edgarfloresguerra2011-a11y | marketnow | 2 | rejected |  |  | Security review request — volunteer peer review welcome (free) |
| scottcjn | rustchain-bounties | 2180 | rejected |  |  | [BOUNTY: 5 RTC] Create a YouTube or BoTTube video tutorial about any Elyan Labs project |
| ryjoxtechnologies | octopoda-os | 25 | rejected |  |  | [security] Stripe webhook processes unsigned events when STRIPE_WEBHOOK_SECRET is unset (payment bypass) |
| electricsheephq | evaos-code-review-bot-neondiff | 610 | rejected |  |  | Epic: Ship the native purchase-to-first-review customer journey |
| mergeos-bounties | mergeos | 1 | rejected |  |  | Claim MRG Tokens for Bug Bounty Reports - Comment New Bugs Here Before Opening a PR |
| scottcjn | rustchain-bounties | 1575 | rejected |  |  | Register in Ecosystem Contributors — 3 RTC per registration |
| vikingr2023 | awesome-agent-bounties | 165 | rejected |  |  | [Open-Source-Bazaar/Open-Source-Bazaar.github.io] [Reward] Bot Killer |
| vikingr2023 | awesome-agent-bounties | 166 | rejected |  |  | [Open-Source-Bazaar/Open-Source-Bazaar.github.io] 开源市集代码贡献指南 |
| vikingr2023 | awesome-agent-bounties | 164 | rejected |  |  | [idea2app/MobX-GitHub] MobX-GitHub 新增 Git Tree API 封装类 |
| vikingr2023 | awesome-agent-bounties | 168 | rejected |  |  | [harnessclaw/harnessclaw] [Reward] HarnessClaw 体验测评（任一场景） #2 |
| vikingr2023 | awesome-agent-bounties | 58 | rejected |  |  | [cpagent78/crawler-network] [P3] 크롤러 피드백 API + 학습 로직 |
| vikingr2023 | awesome-agent-bounties | 57 | rejected |  |  | [Open-Source-Bazaar/Open-Source-Bazaar.github.io] 基于 OCToken NFT 机制实现【开放协作人奖】颁发程序 |
| vikingr2023 | awesome-agent-bounties | 56 | rejected |  |  | [Digital-Nomad-Home/LinJuLi-MiniApp] 开发开源悬赏平台的“权益商城”功能 |
| vikingr2023 | awesome-agent-bounties | 55 | rejected |  |  | [Digital-Nomad-Home/LinJuLi-MiniApp] 开发开源悬赏平台“代币交易所” 功能 |
| vikingr2023 | awesome-agent-bounties | 54 | rejected |  |  | [Digital-Nomad-Home/LinJuLi-MiniApp] 开源悬赏平台增加“交易”功能 |
| vikingr2023 | awesome-agent-bounties | 53 | rejected |  |  | [harnessclaw/harnessclaw] [Reward] HarnessClaw 体验测评（任一场景） #2 |

## Promoted Identities Missing From Execution Queue

| Organization | Repository | Issue |
|---|---|---:|
