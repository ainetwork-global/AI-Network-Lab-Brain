# Global Revenue Brain — Auditoria das Fontes de Descoberta

Gerado em: 2026-07-15T19:49:37.243274+00:00

## Arquivos encontrados

- hunter_sources.json: **sim**
- global_revenue_hunter.py: **sim**
- global_opportunity_scanner.py: **sim**
- run_revenue_pipeline.py: **sim**
- global_revenue_brain.db: **sim**

## Estrutura atual do hunter_sources.json

- `system`: objeto com 8 campos
- `system.name`: `Global Revenue Hunter`
- `system.version`: `1.0.0`
- `system.default_currency`: `USD`
- `system.maximum_results_per_query`: `30`
- `system.request_timeout_seconds`: `20`
- `system.minimum_score_for_review`: `25`
- `system.minimum_score_for_priority`: `55`
- `system.allow_initial_capital`: `False`
- `github_queries`: lista com 8 itens
  - 1. GitHub Bounty Issues
  - 2. GitHub Reward Issues
  - 3. GitHub Paid Issues
  - 4. GitHub Prize Issues
  - 5. GitHub Grant Issues
  - 6. Crypto Bounties
  - 7. AI Agent Bounties
  - 8. MCP Paid Opportunities
- `rss_sources`: lista com 5 itens
  - 1. HackerOne Blog
  - 2. Gitcoin Blog
  - 3. Devpost Blog
  - 4. Mozilla Blog
  - 5. Open Source Initiative
- `positive_keywords`: objeto com 21 campos
- `positive_keywords.bounty`: `25`
- `positive_keywords.reward`: `22`
- `positive_keywords.paid`: `22`
- `positive_keywords.payment`: `18`
- `positive_keywords.prize`: `20`
- `positive_keywords.grant`: `22`
- `positive_keywords.cash`: `18`
- `positive_keywords.usd`: `16`
- `positive_keywords.usdc`: `16`
- `positive_keywords.stipend`: `18`
- `positive_keywords.compensation`: `20`
- `positive_keywords.sponsor`: `10`
- `positive_keywords.hackathon`: `12`
- `positive_keywords.contest`: `12`
- `positive_keywords.freelance`: `15`
- `positive_keywords.contract`: `15`
- `positive_keywords.commission`: `15`
- `positive_keywords.affiliate`: `12`
- `positive_keywords.airdrop`: `8`
- `positive_keywords.testnet reward`: `10`
- `positive_keywords.open source bounty`: `25`
- `negative_keywords`: objeto com 14 campos
- `negative_keywords.unpaid`: `-35`
- `negative_keywords.volunteer only`: `-30`
- `negative_keywords.no compensation`: `-35`
- `negative_keywords.investment required`: `-40`
- `negative_keywords.deposit required`: `-40`
- `negative_keywords.entry fee`: `-30`
- `negative_keywords.purchase required`: `-35`
- `negative_keywords.guaranteed profit`: `-35`
- `negative_keywords.send crypto`: `-40`
- `negative_keywords.seed phrase`: `-60`
- `negative_keywords.private key`: `-60`
- `negative_keywords.casino`: `-45`
- `negative_keywords.betting`: `-45`
- `negative_keywords.loan required`: `-35`

## Funções do Global Revenue Hunter

- `now_iso`
- `build_key`
- `clean_text`
- `load_config`
- `log_error`
- `update_source_health`
- `save_opportunity`
- `scan_github`
- `scan_rss`
- `scan_all`

## Bibliotecas utilizadas pelo Global Revenue Hunter

- `__future__`
- `bs4`
- `database`
- `datetime`
- `feedparser`
- `hashlib`
- `html`
- `json`
- `opportunity_scorer`
- `os`
- `pathlib`
- `re`
- `requests`
- `sys`
- `typing`

## Funções do scanner RSS inicial

- `build_id`
- `ensure_output_file`
- `existing_ids`
- `scan`

## Bibliotecas utilizadas pelo scanner RSS

- `__future__`
- `csv`
- `datetime`
- `feedparser`
- `hashlib`
- `pathlib`

## Funções do pipeline principal

- `run_step`
- `main`

## Registros atuais por fonte

- AI Agent Bounties: **30**
- Crypto Bounties: **30**
- GitHub Grant Issues: **30**
- GitHub Prize Issues: **30**
- GitHub Reward Issues: **30**
- MCP Paid Opportunities: **30**
- GitHub Paid Issues: **27**
- GitHub Bounty Issues: **23**
- Mozilla Blog: **20**
- Open Source Initiative: **10**