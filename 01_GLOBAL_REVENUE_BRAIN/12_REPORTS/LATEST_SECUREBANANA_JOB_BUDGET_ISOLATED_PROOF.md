# SecureBananaLabs — Isolated Job Budget Runtime Proof

Gerado em: 2026-07-17T11:57:01.5990564Z

## Resultado

- Decisão: **RUNTIME_BUG_CONFIRMED**
- Confiança: **98**
- Runtime status: **confirmed_invalid_budget_range_accepted**
- Range inválido aceito: **True**
- Range válido aceito: **True**
- Bug confirmado: **True**
- Schema selecionado: **updateJobSchema**
- Próxima ação: **check_online_duplicate_before_building_fix**

## Ambiente

- Zod instalado no workspace isolado: **sim**
- Versão solicitada: **^3.23.8**
- Origem da versão: **C:\Users\AP10\Revenue-Workspaces\SecureBananaLabs-bug-bounty-743\repository\apps\api\package.json**
- Dependências instaladas no repositório original: **não**
- Código original alterado: **não**

## Schemas detectados

- `createJobSchema`
- `updateJobSchema`

## Tentativas

### Tentativa 1

- Schema: `createJobSchema`
- Payload: **1**
- Range inválido aceito: **False**
- Range válido aceito: **False**

### Tentativa 2

- Schema: `createJobSchema`
- Payload: **2**
- Range inválido aceito: **False**
- Range válido aceito: **False**

### Tentativa 3

- Schema: `createJobSchema`
- Payload: **3**
- Range inválido aceito: **False**
- Range válido aceito: **False**

### Tentativa 4

- Schema: `createJobSchema`
- Payload: **4**
- Range inválido aceito: **False**
- Range válido aceito: **False**

### Tentativa 5

- Schema: `createJobSchema`
- Payload: **5**
- Range inválido aceito: **False**
- Range válido aceito: **False**

### Tentativa 6

- Schema: `updateJobSchema`
- Payload: **1**
- Range inválido aceito: **True**
- Range válido aceito: **True**

## Segurança operacional

- Código original alterado: **não**
- Dependências no repositório original: **não**
- Publicação externa: **não**
- Issue criada: **não**
- Comentário criado: **não**
- Fork criado: **não**
- Pull request criado: **não**
