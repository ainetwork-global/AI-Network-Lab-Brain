# SecureBananaLabs — Reproduction Candidates

Gerado em: 2026-07-17T11:11:30.714557+00:00

## Regra operacional

Nenhum achado abaixo está confirmado como bug.
É obrigatório reproduzir localmente antes de criar qualquer issue.

## Segurança

- Ação externa realizada: **não**
- Issue criada: **não**
- Fork criado: **não**
- Pull request criado: **não**

## Repositório

- Branch: `main`
- Commit: `cac7dea1bd31a7b12c4f02a1a8f6a78139aefd14`
- Arquivos analisados: **74**
- Candidatos estáticos: **12**

## Scripts disponíveis

### `package.json`

- Pacote: `freelance-platform-monorepo`
- `build` → `echo "Run package-specific builds (e.g. npm run build -w apps/web)"`
- `lint` → `echo "No root lint configured"`
- `test` → `npm run test -w apps/api`

### `apps/api/package.json`

- Pacote: `@freelanceflow/api`
- `dev` → `node src/server.js`
- `start` → `node src/server.js`
- `test` → `node --test src/tests`

### `apps/web/package.json`

- Pacote: `@freelanceflow/web`
- `dev` → `next dev -p 3000`
- `build` → `next build`
- `start` → `next start -p 3000`

### `packages/db/package.json`

- Pacote: `@freelanceflow/db`
- `generate` → `prisma generate`
- `migrate` → `prisma migrate dev`

### `packages/ui/package.json`

- Pacote: `@freelanceflow/ui`
- Nenhum script definido.

## Candidatos para reprodução local

### 1. Objeto req.body encaminhado sem seleção explícita

- Arquivo: `apps/api/src/controllers/paymentController.js`
- Linha aproximada: **5**
- Score estático: **87.0**
- Regra: `raw_body_to_service`
- Reprodução: **não realizada**
- Duplicidade online: **não verificada**

Trecho:

```text
return ok(res, await createPaymentIntent(req.body), 201);
```

Próximo teste local:

1. Ler o arquivo e identificar a intenção da função.
2. Criar um teste mínimo que falhe no comportamento atual.
3. Confirmar que o teste falha antes de qualquer correção.
4. Verificar se o mesmo problema já foi reportado.
5. Somente então preparar uma proposta de correção.

### 2. Objeto req.body encaminhado sem seleção explícita

- Arquivo: `apps/api/src/controllers/messageController.js`
- Linha aproximada: **9**
- Score estático: **87.0**
- Regra: `raw_body_to_service`
- Reprodução: **não realizada**
- Duplicidade online: **não verificada**

Trecho:

```text
return ok(res, await sendMessage(req.body), 201);
```

Próximo teste local:

1. Ler o arquivo e identificar a intenção da função.
2. Criar um teste mínimo que falhe no comportamento atual.
3. Confirmar que o teste falha antes de qualquer correção.
4. Verificar se o mesmo problema já foi reportado.
5. Somente então preparar uma proposta de correção.

### 3. Objeto req.body encaminhado sem seleção explícita

- Arquivo: `apps/api/src/controllers/notificationController.js`
- Linha aproximada: **9**
- Score estático: **87.0**
- Regra: `raw_body_to_service`
- Reprodução: **não realizada**
- Duplicidade online: **não verificada**

Trecho:

```text
return ok(res, await createNotification(req.body), 201);
```

Próximo teste local:

1. Ler o arquivo e identificar a intenção da função.
2. Criar um teste mínimo que falhe no comportamento atual.
3. Confirmar que o teste falha antes de qualquer correção.
4. Verificar se o mesmo problema já foi reportado.
5. Somente então preparar uma proposta de correção.

### 4. Objeto req.body encaminhado sem seleção explícita

- Arquivo: `apps/api/src/controllers/proposalController.js`
- Linha aproximada: **9**
- Score estático: **87.0**
- Regra: `raw_body_to_service`
- Reprodução: **não realizada**
- Duplicidade online: **não verificada**

Trecho:

```text
return ok(res, await createProposal(req.body), 201);
```

Próximo teste local:

1. Ler o arquivo e identificar a intenção da função.
2. Criar um teste mínimo que falhe no comportamento atual.
3. Confirmar que o teste falha antes de qualquer correção.
4. Verificar se o mesmo problema já foi reportado.
5. Somente então preparar uma proposta de correção.

### 5. Objeto req.body encaminhado sem seleção explícita

- Arquivo: `apps/api/src/controllers/reviewController.js`
- Linha aproximada: **9**
- Score estático: **87.0**
- Regra: `raw_body_to_service`
- Reprodução: **não realizada**
- Duplicidade online: **não verificada**

Trecho:

```text
return ok(res, await createReview(req.body), 201);
```

Próximo teste local:

1. Ler o arquivo e identificar a intenção da função.
2. Criar um teste mínimo que falhe no comportamento atual.
3. Confirmar que o teste falha antes de qualquer correção.
4. Verificar se o mesmo problema já foi reportado.
5. Somente então preparar uma proposta de correção.

### 6. Objeto req.body encaminhado sem seleção explícita

- Arquivo: `apps/api/src/controllers/userController.js`
- Linha aproximada: **9**
- Score estático: **87.0**
- Regra: `raw_body_to_service`
- Reprodução: **não realizada**
- Duplicidade online: **não verificada**

Trecho:

```text
return ok(res, await createUser(req.body), 201);
```

Próximo teste local:

1. Ler o arquivo e identificar a intenção da função.
2. Criar um teste mínimo que falhe no comportamento atual.
3. Confirmar que o teste falha antes de qualquer correção.
4. Verificar se o mesmo problema já foi reportado.
5. Somente então preparar uma proposta de correção.

### 7. Upload possivelmente aceita arquivo vazio ou ausente

- Arquivo: `apps/api/src/controllers/uploadController.js`
- Linha aproximada: **5**
- Score estático: **85.0**
- Regra: `empty_upload_acceptance`
- Reprodução: **não realizada**
- Duplicidade online: **não verificada**

Trecho:

```text
filename: req.file?.originalname ?? null,
```

Próximo teste local:

1. Ler o arquivo e identificar a intenção da função.
2. Criar um teste mínimo que falhe no comportamento atual.
3. Confirmar que o teste falha antes de qualquer correção.
4. Verificar se o mesmo problema já foi reportado.
5. Somente então preparar uma proposta de correção.

### 8. Lógica de produção marcada como TODO/FIXME

- Arquivo: `apps/api/src/config/db.js`
- Linha aproximada: **2**
- Score estático: **80.0**
- Regra: `todo_business_logic`
- Reprodução: **não realizada**
- Duplicidade online: **não verificada**

Trecho:

```text
// TODO: wire Prisma client from @freelanceflow/db package
```

Próximo teste local:

1. Ler o arquivo e identificar a intenção da função.
2. Criar um teste mínimo que falhe no comportamento atual.
3. Confirmar que o teste falha antes de qualquer correção.
4. Verificar se o mesmo problema já foi reportado.
5. Somente então preparar uma proposta de correção.

### 9. Lógica de produção marcada como TODO/FIXME

- Arquivo: `apps/api/src/services/paymentService.js`
- Linha aproximada: **2**
- Score estático: **80.0**
- Regra: `todo_business_logic`
- Reprodução: **não realizada**
- Duplicidade online: **não verificada**

Trecho:

```text
// TODO: integrate Stripe SDK and return client secret.
```

Próximo teste local:

1. Ler o arquivo e identificar a intenção da função.
2. Criar um teste mínimo que falhe no comportamento atual.
3. Confirmar que o teste falha antes de qualquer correção.
4. Verificar se o mesmo problema já foi reportado.
5. Somente então preparar uma proposta de correção.

### 10. Lógica de produção marcada como TODO/FIXME

- Arquivo: `apps/api/src/services/searchService.js`
- Linha aproximada: **2**
- Score estático: **80.0**
- Regra: `todo_business_logic`
- Reprodução: **não realizada**
- Duplicidade online: **não verificada**

Trecho:

```text
// TODO: use PostgreSQL full-text search + ranking.
```

Próximo teste local:

1. Ler o arquivo e identificar a intenção da função.
2. Criar um teste mínimo que falhe no comportamento atual.
3. Confirmar que o teste falha antes de qualquer correção.
4. Verificar se o mesmo problema já foi reportado.
5. Somente então preparar uma proposta de correção.

### 11. Lógica de produção marcada como TODO/FIXME

- Arquivo: `apps/api/src/services/authService.js`
- Linha aproximada: **4**
- Score estático: **80.0**
- Regra: `todo_business_logic`
- Reprodução: **não realizada**
- Duplicidade online: **não verificada**

Trecho:

```text
// TODO: persist new user via Prisma
```

Próximo teste local:

1. Ler o arquivo e identificar a intenção da função.
2. Criar um teste mínimo que falhe no comportamento atual.
3. Confirmar que o teste falha antes de qualquer correção.
4. Verificar se o mesmo problema já foi reportado.
5. Somente então preparar uma proposta de correção.

### 12. Validação numérica possivelmente incompleta

- Arquivo: `apps/api/src/validators/job.js`
- Linha aproximada: **6**
- Score estático: **77.0**
- Regra: `unsafe_numeric_range`
- Reprodução: **não realizada**
- Duplicidade online: **não verificada**

Trecho:

```text
budgetMin: z.number().nonnegative(),
```

Próximo teste local:

1. Ler o arquivo e identificar a intenção da função.
2. Criar um teste mínimo que falhe no comportamento atual.
3. Confirmar que o teste falha antes de qualquer correção.
4. Verificar se o mesmo problema já foi reportado.
5. Somente então preparar uma proposta de correção.

## Decisão

**Selecionar apenas um candidato para reprodução local. Não criar issue enquanto não houver teste falhando e checagem de duplicidade.**