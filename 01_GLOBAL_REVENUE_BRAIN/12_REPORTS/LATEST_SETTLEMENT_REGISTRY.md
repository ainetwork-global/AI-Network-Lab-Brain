# Global Revenue Brain — Settlement Registry

Gerado em: 2026-07-16T18:37:28.573865+00:00

Nenhum segredo, chave, endereço bancário ou credencial foi gravado.

## Destinos

### Stripe Commercial Revenue

- Chave: `stripe_commercial`
- Provedor: Stripe
- Rail: card_and_stripe_payments
- Moedas: USD,BRL
- Configuração: **existing_configuration_to_verify**
- Verificação: **pending_live_receipt_test**
- Detecção automática: sim
- Reconciliação automática: sim
- Observação: Preferencial para SaaS, assinaturas, créditos, serviços e pagamentos comerciais.

### Base USDC Treasury Wallet

- Chave: `base_usdc_wallet`
- Provedor: Base
- Rail: onchain_usdc
- Moedas: USDC
- Configuração: **existing_configuration_to_verify**
- Verificação: **pending_live_receipt_test**
- Detecção automática: sim
- Reconciliação automática: sim
- Observação: Preferencial para recompensas on-chain, agentes, micropagamentos e oportunidades que paguem em USDC.

### Nomad USD Account

- Chave: `nomad_usd`
- Provedor: Nomad
- Rail: bank_transfer
- Moedas: USD
- Configuração: **account_details_to_verify**
- Verificação: **pending_receipt_test**
- Detecção automática: não
- Reconciliação automática: não
- Observação: Preferencial quando o pagador oferecer transferência bancária em USD compatível com os dados da conta.
