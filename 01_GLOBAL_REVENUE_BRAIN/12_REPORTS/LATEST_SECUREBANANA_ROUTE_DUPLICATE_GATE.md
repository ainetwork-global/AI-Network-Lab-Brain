# SecureBananaLabs — Route and Duplicate Gate

Gerado em: 2026-07-17T14:12:05.473952+00:00

## Resultado

- Decisão: **ALL_TESTED_BODY_FLOWS_OCCUPIED**
- Próxima ação: **move_to_next_static_candidate_class**

## Resultados por fluxo

### message

- Decisão: **DUPLICATE_OR_OCCUPIED**
- Autenticação detectada: **False**
- Validação detectada: **False**
- Route risk: **no_auth_or_validation_detected**
- Duplicata bloqueadora: **True**
- Duplicatas conhecidas: **0**
- Correspondências fortes: **10**

#### Rotas identificadas

- `apps/api/src/routes/messageRoutes.js:7` — `messageRoutes.post("/", postMessage);`

#### Duplicatas conhecidas

- Nenhuma duplicata pré-confirmada.

#### Correspondências online fortes

- #10875 — Message service should generate collision-resistant server-owned ids (relevância 95)
- #7373 — fix: job, review, and message services should not allow client-controlled id override (relevância 95)
- #7268 — Message creation should preserve server-generated id (relevância 85)
- #5939 — Bug: Message creation accepts client-controlled id field (relevância 85)
- #5933 — Message creation should keep message ids server-owned (relevância 85)
- #3426 — Message service should keep ids and stored records server-owned (relevância 85)
- #9036 — Message and job creation allow client-controlled field injection via object spread (Yzgaming005) (relevância 75)
- #8080 — Message creation should validate required fields and preserve server-owned ids (LokiLiu reissue via #743) (relevância 75)
- #8058 — Message creation should validate required fields and preserve server-owned ids (relevância 75)
- #7520 — messageService.sendMessage allows caller to override server-assigned id and sentAt (relevância 75)

### notification

- Decisão: **DUPLICATE_OR_OCCUPIED**
- Autenticação detectada: **False**
- Validação detectada: **False**
- Route risk: **no_auth_or_validation_detected**
- Duplicata bloqueadora: **True**
- Duplicatas conhecidas: **1**
- Correspondências fortes: **10**

#### Rotas identificadas

- `apps/api/src/routes/notificationRoutes.js:7` — `notificationRoutes.post("/", postNotification);`

#### Duplicatas conhecidas

- #2762 — Notification creation should preserve server-owned id and read state

#### Correspondências online fortes

- #10873 — Notification service should generate collision-resistant server-owned ids (relevância 95)
- #9317 — fix: notification creation should preserve server-owned id and read state (relevância 85)
- #2762 — Notification creation should preserve server-owned id and read state (relevância 85)
- #7489 — notificationService.createNotification allows caller to override server-owned id and read state (relevância 85)
- #7249 — Notification creation should preserve server-owned id and read state (relevância 85)
- #5715 — Notification creation should preserve server-owned id and read state (relevância 85)
- #5169 — Notification creation should preserve server-owned id and unread state (relevância 85)
- #4255 — Notification creation should preserve server-owned id and unread state (relevância 85)
- #3612 — Notification creation should preserve server-owned id and read state (relevância 85)
- #2010 — Notification creation should use server-owned unread status (relevância 85)

### proposal

- Decisão: **DUPLICATE_OR_OCCUPIED**
- Autenticação detectada: **False**
- Validação detectada: **False**
- Route risk: **no_auth_or_validation_detected**
- Duplicata bloqueadora: **True**
- Duplicatas conhecidas: **0**
- Correspondências fortes: **10**

#### Rotas identificadas

- `apps/api/src/routes/proposalRoutes.js:7` — `proposalRoutes.post("/", postProposal);`

#### Duplicatas conhecidas

- Nenhuma duplicata pré-confirmada.

#### Correspondências online fortes

- #2041 — Proposal creation should not allow caller-controlled ids (relevância 85)
- #8035 — Proposal creation should validate required fields and preserve server-owned ids (relevância 75)
- #6661 — Proposal creation should preserve server-generated ids (MolhamHamwi reissue via #743) (relevância 75)
- #6443 — Proposal creation should preserve server-generated id (relevância 75)
- #6182 — Proposal creation should validate payloads and preserve server-owned ids (reissue) (relevância 75)
- #5999 — Proposal creation should preserve a server-generated id (relevância 75)
- #5872 — Proposal creation should preserve a server-generated id (relevância 75)
- #5309 — Proposal creation should whitelist public fields before persistence (relevância 75)
- #4249 — Proposal creation should preserve server-generated id (relevância 75)
- #4092 — Proposal creation should preserve server-generated id (relevância 75)

### review

- Decisão: **DUPLICATE_OR_OCCUPIED**
- Autenticação detectada: **False**
- Validação detectada: **False**
- Route risk: **no_auth_or_validation_detected**
- Duplicata bloqueadora: **True**
- Duplicatas conhecidas: **0**
- Correspondências fortes: **10**

#### Rotas identificadas

- `apps/api/src/routes/reviewRoutes.js:7` — `reviewRoutes.post("/", postReview);`

#### Duplicatas conhecidas

- Nenhuma duplicata pré-confirmada.

#### Correspondências online fortes

- #7373 — fix: job, review, and message services should not allow client-controlled id override (relevância 95)
- #2048 — Review creation should not allow caller-controlled ids (relevância 85)
- #10859 — Review service should generate collision-resistant server-owned ids (relevância 75)
- #8082 — Review creation should validate required fields and preserve server-owned ids (LokiLiu reissue via #743) (relevância 75)
- #8050 — Review creation should validate required fields and preserve server-owned ids (relevância 75)
- #6843 — Review creation accepts client-controlled id and invalid ratings (relevância 75)
- #6651 — Review creation should preserve server-generated id (MolhamHamwi reissue via #743) (relevância 75)
- #6632 — Review creation should preserve server-generated id (YfengJ reissue via #743) (relevância 75)
- #6482 — Review creation should preserve server-generated id (reissue via #743) (relevância 75)
- #6459 — Review creation should preserve server-generated id (relevância 75)

### user

- Decisão: **DUPLICATE_OR_OCCUPIED**
- Autenticação detectada: **True**
- Validação detectada: **True**
- Route risk: **validated_authenticated**
- Duplicata bloqueadora: **True**
- Duplicatas conhecidas: **1**
- Correspondências fortes: **10**

#### Rotas identificadas

- `apps/api/src/routes/userRoutes.js:7` — `userRoutes.post("/", postUser);`

#### Duplicatas conhecidas

- #802 — User creation accepts empty payloads and client-controlled IDs

#### Correspondências online fortes

- #7565 — User service should not allow client-controlled id override (relevância 85)
- #7372 — fix: user service should not allow client-controlled id override (relevância 85)
- #4261 — User creation should keep server-generated ids (relevância 85)
- #802 — User creation accepts empty payloads and client-controlled IDs (relevância 85)
- #6658 — User creation should preserve server-generated ids (MolhamHamwi reissue via #743) (relevância 75)
- #3058 — Record creation endpoints allow client-supplied IDs to override server IDs (relevância 75)
- #2587 — Mirror: User creation should ignore caller-supplied ids (relevância 75)
- #2534 — User creation should ignore caller-supplied ids (relevância 75)
- #10984 — User creation accepts empty payloads and client-controlled ids (relevância 65)
- #7606 — userService exposes mutable internal state and allows id injection (relevância 65)

## Segurança operacional

- Pesquisa GitHub: **somente leitura**
- Código original alterado: **não**
- Dependências instaladas: **não**
- Issue criada: **não**
- Comentário criado: **não**
- Fork criado: **não**
- Pull request criado: **não**