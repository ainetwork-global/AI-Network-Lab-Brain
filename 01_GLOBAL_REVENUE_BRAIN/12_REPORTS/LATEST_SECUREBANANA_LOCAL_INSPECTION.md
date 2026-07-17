# SecureBananaLabs #743 — Local Repository Inspection

Gerado em: 2026-07-17T10:51:57.114190+00:00

## Segurança operacional

- Inspeção somente local: **sim**
- Issue criada: **não**
- Comentário publicado: **não**
- Fork criado: **não**
- Pull request criado: **não**
- Código externo submetido: **não**

## Repositório

- Remote: `https://github.com/SecureBananaLabs/bug-bounty.git`
- Branch: `main`
- Commit analisado: `cac7dea1bd31a7b12c4f02a1a8f6a78139aefd14`
- Arquivos de texto/código analisados: **77**

## Tecnologias encontradas

- JavaScript: 45 arquivo(s)
- TypeScript/React: 17 arquivo(s)
- TypeScript: 4 arquivo(s)
- CSS: 1 arquivo(s)

## Arquivos de configuração

- `package.json`

## READMEs

- `README.md`

## Testes encontrados

- `apps/api/src/tests/health.test.js`

## Marcadores de possível manutenção

- `leaderboard.json:123` — `TODO` — "TodouWisiper": 1,
- `package-lock.json:1832` — `XXX` — "integrity": "sha512-YZo3K82SD7Riyi0E1EQPojLz7kpepnSQI9IyPbHHg1XXXevb5dJI7tpyN2ADxGcQbHG7vcyRHk0cbwqcQriUtg==",
- `package-lock.json:2173` — `HACK` — "url": "https://github.com/sponsors/colinhacks"
- `apps/api/src/server.js:9` — `console.log` — console.log(`API listening on http://localhost:${env.port}`);
- `apps/api/src/config/db.js:2` — `TODO` — // TODO: wire Prisma client from @freelanceflow/db package
- `apps/api/src/services/authService.js:4` — `TODO` — // TODO: persist new user via Prisma
- `apps/api/src/services/authService.js:14` — `TODO` — // TODO: verify password hash against stored user record
- `apps/api/src/services/authService.js:14` — `pass` — // TODO: verify password hash against stored user record
- `apps/api/src/services/paymentService.js:2` — `TODO` — // TODO: integrate Stripe SDK and return client secret.
- `apps/api/src/services/searchService.js:2` — `TODO` — // TODO: use PostgreSQL full-text search + ranking.
- `apps/api/src/validators/auth.js:5` — `pass` — password: z.string().min(8),
- `apps/api/src/validators/auth.js:11` — `pass` — password: z.string().min(8)

## Arquivos candidatos para inspeção detalhada

### 1. `apps/api/src/services/authService.js`

- Score de inspeção: **59.0**
- Linhas: 23
- Marcadores: 3
- Motivos: 3 marcador(es) de manutenção, arquivo de escopo pequeno, arquivo executável ou de lógica

### 2. `apps/api/src/validators/auth.js`

- Score de inspeção: **51.0**
- Linhas: 12
- Marcadores: 2
- Motivos: 2 marcador(es) de manutenção, arquivo de escopo pequeno, arquivo executável ou de lógica

### 3. `apps/web/next.config.js`

- Score de inspeção: **45.0**
- Linhas: 4
- Marcadores: 0
- Motivos: arquivo de escopo pequeno, arquivo executável ou de lógica, componente potencialmente isolado

### 4. `apps/api/src/config/db.js`

- Score de inspeção: **43.0**
- Linhas: 4
- Marcadores: 1
- Motivos: 1 marcador(es) de manutenção, arquivo de escopo pequeno, arquivo executável ou de lógica

### 5. `apps/api/src/services/paymentService.js`

- Score de inspeção: **43.0**
- Linhas: 9
- Marcadores: 1
- Motivos: 1 marcador(es) de manutenção, arquivo de escopo pequeno, arquivo executável ou de lógica

### 6. `apps/api/src/services/searchService.js`

- Score de inspeção: **43.0**
- Linhas: 9
- Marcadores: 1
- Motivos: 1 marcador(es) de manutenção, arquivo de escopo pequeno, arquivo executável ou de lógica

### 7. `apps/api/src/server.js`

- Score de inspeção: **43.0**
- Linhas: 13
- Marcadores: 1
- Motivos: 1 marcador(es) de manutenção, arquivo de escopo pequeno, arquivo executável ou de lógica

### 8. `packages/db/src/index.ts`

- Score de inspeção: **35.0**
- Linhas: 1
- Marcadores: 0
- Motivos: arquivo de escopo pequeno, arquivo executável ou de lógica

### 9. `packages/ui/src/index.ts`

- Score de inspeção: **35.0**
- Linhas: 2
- Marcadores: 0
- Motivos: arquivo de escopo pequeno, arquivo executável ou de lógica

### 10. `apps/web/next-env.d.ts`

- Score de inspeção: **35.0**
- Linhas: 6
- Marcadores: 0
- Motivos: arquivo de escopo pequeno, arquivo executável ou de lógica

### 11. `apps/api/src/controllers/adminController.js`

- Score de inspeção: **35.0**
- Linhas: 6
- Marcadores: 0
- Motivos: arquivo de escopo pequeno, arquivo executável ou de lógica

### 12. `apps/api/src/controllers/paymentController.js`

- Score de inspeção: **35.0**
- Linhas: 6
- Marcadores: 0
- Motivos: arquivo de escopo pequeno, arquivo executável ou de lógica

### 13. `apps/api/src/controllers/searchController.js`

- Score de inspeção: **35.0**
- Linhas: 6
- Marcadores: 0
- Motivos: arquivo de escopo pequeno, arquivo executável ou de lógica

### 14. `apps/api/src/routes/paymentRoutes.js`

- Score de inspeção: **35.0**
- Linhas: 6
- Marcadores: 0
- Motivos: arquivo de escopo pequeno, arquivo executável ou de lógica

### 15. `apps/api/src/routes/searchRoutes.js`

- Score de inspeção: **35.0**
- Linhas: 6
- Marcadores: 0
- Motivos: arquivo de escopo pequeno, arquivo executável ou de lógica

### 16. `apps/api/src/config/env.js`

- Score de inspeção: **35.0**
- Linhas: 7
- Marcadores: 0
- Motivos: arquivo de escopo pequeno, arquivo executável ou de lógica

### 17. `apps/api/src/routes/jobRoutes.js`

- Score de inspeção: **35.0**
- Linhas: 7
- Marcadores: 0
- Motivos: arquivo de escopo pequeno, arquivo executável ou de lógica

### 18. `apps/api/src/routes/messageRoutes.js`

- Score de inspeção: **35.0**
- Linhas: 7
- Marcadores: 0
- Motivos: arquivo de escopo pequeno, arquivo executável ou de lógica

### 19. `apps/api/src/routes/notificationRoutes.js`

- Score de inspeção: **35.0**
- Linhas: 7
- Marcadores: 0
- Motivos: arquivo de escopo pequeno, arquivo executável ou de lógica

### 20. `apps/api/src/routes/proposalRoutes.js`

- Score de inspeção: **35.0**
- Linhas: 7
- Marcadores: 0
- Motivos: arquivo de escopo pequeno, arquivo executável ou de lógica

### 21. `apps/api/src/routes/reviewRoutes.js`

- Score de inspeção: **35.0**
- Linhas: 7
- Marcadores: 0
- Motivos: arquivo de escopo pequeno, arquivo executável ou de lógica

### 22. `apps/api/src/routes/userRoutes.js`

- Score de inspeção: **35.0**
- Linhas: 7
- Marcadores: 0
- Motivos: arquivo de escopo pequeno, arquivo executável ou de lógica

### 23. `apps/api/src/utils/response.js`

- Score de inspeção: **35.0**
- Linhas: 7
- Marcadores: 0
- Motivos: arquivo de escopo pequeno, arquivo executável ou de lógica

### 24. `apps/api/src/controllers/uploadController.js`

- Score de inspeção: **35.0**
- Linhas: 8
- Marcadores: 0
- Motivos: arquivo de escopo pequeno, arquivo executável ou de lógica

### 25. `apps/api/src/middleware/rateLimit.js`

- Score de inspeção: **35.0**
- Linhas: 8
- Marcadores: 0
- Motivos: arquivo de escopo pequeno, arquivo executável ou de lógica

### 26. `apps/api/src/routes/adminRoutes.js`

- Score de inspeção: **35.0**
- Linhas: 8
- Marcadores: 0
- Motivos: arquivo de escopo pequeno, arquivo executável ou de lógica

### 27. `apps/api/src/services/adminService.js`

- Score de inspeção: **35.0**
- Linhas: 8
- Marcadores: 0
- Motivos: arquivo de escopo pequeno, arquivo executável ou de lógica

### 28. `apps/web/app/page.tsx`

- Score de inspeção: **35.0**
- Linhas: 8
- Marcadores: 0
- Motivos: arquivo de escopo pequeno, arquivo executável ou de lógica

### 29. `apps/web/app/admin/page.tsx`

- Score de inspeção: **35.0**
- Linhas: 8
- Marcadores: 0
- Motivos: arquivo de escopo pequeno, arquivo executável ou de lógica

### 30. `apps/web/app/billing/page.tsx`

- Score de inspeção: **35.0**
- Linhas: 8
- Marcadores: 0
- Motivos: arquivo de escopo pequeno, arquivo executável ou de lógica

## Próximo gate

Escolher um único comportamento pequeno, reproduzível e testável. Nenhuma issue deverá ser criada antes de existir reprodução local e proposta técnica objetiva.