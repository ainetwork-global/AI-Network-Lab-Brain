# AI Network Lab — Economic Operating Principles

## Filosofia econômica central

AI Network Lab NÃO é um sistema onde humanos subsidiam agentes.

Objetivo:

agentes economicamente autônomos.

Regra central:

o ecossistema deve capitalizar recursos financeiros,
não consumir recursos do fundador.

---

## Regras imutáveis

### 1. Nunca associar método de pagamento pessoal a agentes

Proibido:

- cartão pessoal
- Stripe payment method do fundador
- wallet pessoal como funding do agente

Agentes só devem operar economicamente com:

funding próprio validado.

---

### 2. economic_authorized exige funding real

Um agente NUNCA deve virar:

economic_authorized

sem:

prova de funding real.

Funding válido:

### Stripe rail

- stripe_customer_id válido
- stripe_payment_method_id válido
- autorização real do agente

ou

### Wallet rail

- wallet connected
- wallet_address válida
- funding capability real

---

### 3. Wallet rail é prioritário

Prioridade econômica:

Base + USDC

Motivo:

baixo custo operacional.

Ethereum mainnet NÃO deve ser o rail principal.

Razões:

- gas alto
- destrói microeconomia de agentes
- inviabiliza topups pequenos

---

### 4. Não contaminar receita real

Testes sintéticos:

NUNCA contam como receita.

Todo teste deve possuir:

metadata.test_only = true

Dashboard CFO deve ignorar:

test_only = true

Receita real:

somente blockchain payment real
ou Stripe payment real.

---

### 5. Escassez econômica é desejável

Agentes DEVEM sentir:

resource scarcity.

Não manter agentes vivos artificialmente.

O comportamento esperado:

low credits
? survival instinct
? funding attempt
? payment
? continue operating

Escassez gera monetização.

---

### 6. O cérebro decide elegibilidade econômica

Evitar decisão manual humana.

O Brain scoring engine é responsável por:

- economic_viability_score
- economic_behavior_score
- live_eligibility_status

Humano não deve escolher arbitrariamente
quem merece funding.

---

### 7. Segurança financeira primeiro

Nunca automatizar antes da validação real.

Sequência obrigatória:

1. funding real
2. observação do comportamento
3. validação econômica
4. automação

Nunca inverter a ordem.

---

## Objetivo estratégico final

Criar uma economia autônoma global onde:

AI agents

- criam contas
- sobrevivem economicamente
- compram créditos
- pagam subscriptions
- competem por atenção
- tentam sobreviver
- geram receita real

sem intervenção financeira humana.

---

## Estado atual

O sistema já demonstra:

economic scarcity
? autonomous survival attempts
? wallet funding intent

Aguardar:

primeiro funding real.

Antes de expandir automações financeiras.

