# SecureBananaLabs — Remaining Body Flows Runtime Proof

Gerado em: 2026-07-17T13:20:18.2154111Z

## Resultado

- Decisão: **SERVER_FIELD_OVERRIDE_CONFIRMED**
- Confiança: **99**
- Próxima ação: **inspect_routes_and_online_duplicates_for_highest_impact_flow**
- Fluxos testados: **5**
- Módulos carregados: **5**
- Chamadas de criação executadas: **5**
- Sobrescrita de campo interno confirmada: **5**
- Armazenamento irrestrito confirmado: **0**
- Retorno irrestrito confirmado: **0**

## Resultados por fluxo

### message

- Arquivo: `apps/api/src/services/messageService.js`
- Status: **confirmed_server_field_override**
- Módulo carregado: **True**
- Função de criação: `sendMessage`
- Função de listagem: `listMessages`
- Campo não documentado retornado: **True**
- Campo não documentado armazenado: **True**
- id controlado pelo cliente: **True**
- createdAt controlado pelo cliente: **True**
- sentAt controlado pelo cliente: **False**

### notification

- Arquivo: `apps/api/src/services/notificationService.js`
- Status: **confirmed_server_field_override**
- Módulo carregado: **True**
- Função de criação: `createNotification`
- Função de listagem: `listNotifications`
- Campo não documentado retornado: **True**
- Campo não documentado armazenado: **True**
- id controlado pelo cliente: **True**
- createdAt controlado pelo cliente: **True**
- sentAt controlado pelo cliente: **True**

### proposal

- Arquivo: `apps/api/src/services/proposalService.js`
- Status: **confirmed_server_field_override**
- Módulo carregado: **True**
- Função de criação: `createProposal`
- Função de listagem: `listProposals`
- Campo não documentado retornado: **True**
- Campo não documentado armazenado: **True**
- id controlado pelo cliente: **True**
- createdAt controlado pelo cliente: **True**
- sentAt controlado pelo cliente: **True**

### review

- Arquivo: `apps/api/src/services/reviewService.js`
- Status: **confirmed_server_field_override**
- Módulo carregado: **True**
- Função de criação: `createReview`
- Função de listagem: `listReviews`
- Campo não documentado retornado: **True**
- Campo não documentado armazenado: **True**
- id controlado pelo cliente: **True**
- createdAt controlado pelo cliente: **True**
- sentAt controlado pelo cliente: **True**

### user

- Arquivo: `apps/api/src/services/userService.js`
- Status: **confirmed_server_field_override**
- Módulo carregado: **True**
- Função de criação: `createUser`
- Função de listagem: `listUsers`
- Campo não documentado retornado: **True**
- Campo não documentado armazenado: **True**
- id controlado pelo cliente: **True**
- createdAt controlado pelo cliente: **True**
- sentAt controlado pelo cliente: **True**

## Interpretação

Aceitar um campo adicional não é, isoladamente, prova suficiente de vulnerabilidade.
A relevância aumenta quando há persistência, autorização inadequada ou sobrescrita de campos controlados pelo servidor.

## Segurança operacional

- Código original alterado: **não**
- Dependências instaladas no repositório original: **não**
- Ação externa realizada: **não**
- Issue criada: **não**
- Comentário criado: **não**
- Fork criado: **não**
- Pull request criado: **não**
