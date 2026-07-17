# SecureBananaLabs — Local Proof Engine

Gerado em: 2026-07-17T11:20:57.359598+00:00

## Regra

Evidência estática forte ainda não representa bug confirmado. É necessário teste local reproduzível antes de qualquer publicação.

## Segurança operacional

- Código-fonte alterado: **não**
- Ação externa realizada: **não**
- Issue criada: **não**
- Fork criado: **não**
- Pull request criado: **não**

## Resumo

- Candidatos analisados: **12**
- Evidência estática forte: **9**
- Reprodução em runtime necessária: **3**
- Prováveis falsos positivos: **0**

## Ranking de provas

### 1. Objeto req.body encaminhado sem seleção explícita

- Arquivo: `apps/api/src/controllers/paymentController.js`
- Linha aproximada: 5
- Regra: `raw_body_to_service`
- Status: **strong_static_evidence**
- Proof score: **97.0**

Evidências:

- req.body é encaminhado integralmente: createPaymentIntent(req.body)

Contraevidências:

- Sintaxe JavaScript válida.

Teste local sugerido:

- Enviar campo extra não documentado no payload e verificar se ele chega ao serviço ou persistência. O teste deve usar mocks locais e não chamar serviços externos.

Arquivos relacionados:

- `apps/api/src/utils/response.js`
- `apps/api/src/services/paymentService.js`

Testes relacionados:

- Nenhum teste relacionado identificado.

### 2. Objeto req.body encaminhado sem seleção explícita

- Arquivo: `apps/api/src/controllers/messageController.js`
- Linha aproximada: 9
- Regra: `raw_body_to_service`
- Status: **strong_static_evidence**
- Proof score: **97.0**

Evidências:

- req.body é encaminhado integralmente: sendMessage(req.body)

Contraevidências:

- Sintaxe JavaScript válida.

Teste local sugerido:

- Enviar campo extra não documentado no payload e verificar se ele chega ao serviço ou persistência. O teste deve usar mocks locais e não chamar serviços externos.

Arquivos relacionados:

- `apps/api/src/utils/response.js`
- `apps/api/src/services/messageService.js`

Testes relacionados:

- Nenhum teste relacionado identificado.

### 3. Objeto req.body encaminhado sem seleção explícita

- Arquivo: `apps/api/src/controllers/notificationController.js`
- Linha aproximada: 9
- Regra: `raw_body_to_service`
- Status: **strong_static_evidence**
- Proof score: **97.0**

Evidências:

- req.body é encaminhado integralmente: createNotification(req.body)

Contraevidências:

- Sintaxe JavaScript válida.

Teste local sugerido:

- Enviar campo extra não documentado no payload e verificar se ele chega ao serviço ou persistência. O teste deve usar mocks locais e não chamar serviços externos.

Arquivos relacionados:

- `apps/api/src/utils/response.js`
- `apps/api/src/services/notificationService.js`

Testes relacionados:

- Nenhum teste relacionado identificado.

### 4. Objeto req.body encaminhado sem seleção explícita

- Arquivo: `apps/api/src/controllers/proposalController.js`
- Linha aproximada: 9
- Regra: `raw_body_to_service`
- Status: **strong_static_evidence**
- Proof score: **97.0**

Evidências:

- req.body é encaminhado integralmente: createProposal(req.body)

Contraevidências:

- Sintaxe JavaScript válida.

Teste local sugerido:

- Enviar campo extra não documentado no payload e verificar se ele chega ao serviço ou persistência. O teste deve usar mocks locais e não chamar serviços externos.

Arquivos relacionados:

- `apps/api/src/utils/response.js`
- `apps/api/src/services/proposalService.js`

Testes relacionados:

- Nenhum teste relacionado identificado.

### 5. Objeto req.body encaminhado sem seleção explícita

- Arquivo: `apps/api/src/controllers/reviewController.js`
- Linha aproximada: 9
- Regra: `raw_body_to_service`
- Status: **strong_static_evidence**
- Proof score: **97.0**

Evidências:

- req.body é encaminhado integralmente: createReview(req.body)

Contraevidências:

- Sintaxe JavaScript válida.

Teste local sugerido:

- Enviar campo extra não documentado no payload e verificar se ele chega ao serviço ou persistência. O teste deve usar mocks locais e não chamar serviços externos.

Arquivos relacionados:

- `apps/api/src/utils/response.js`
- `apps/api/src/services/reviewService.js`

Testes relacionados:

- Nenhum teste relacionado identificado.

### 6. Objeto req.body encaminhado sem seleção explícita

- Arquivo: `apps/api/src/controllers/userController.js`
- Linha aproximada: 9
- Regra: `raw_body_to_service`
- Status: **strong_static_evidence**
- Proof score: **97.0**

Evidências:

- req.body é encaminhado integralmente: createUser(req.body)

Contraevidências:

- Sintaxe JavaScript válida.

Teste local sugerido:

- Enviar campo extra não documentado no payload e verificar se ele chega ao serviço ou persistência. O teste deve usar mocks locais e não chamar serviços externos.

Arquivos relacionados:

- `apps/api/src/utils/response.js`
- `apps/api/src/services/userService.js`

Testes relacionados:

- Nenhum teste relacionado identificado.

### 7. Upload possivelmente aceita arquivo vazio ou ausente

- Arquivo: `apps/api/src/controllers/uploadController.js`
- Linha aproximada: 5
- Regra: `empty_upload_acceptance`
- Status: **strong_static_evidence**
- Proof score: **97.0**

Evidências:

- Controller acessa req.file ou req.files.
- Nenhuma guarda explícita foi localizada no controller.

Contraevidências:

- Sintaxe JavaScript válida.

Teste local sugerido:

- Invocar o handler com req.file ausente, arquivo de tamanho zero e lista vazia; confirmar o status HTTP e se ocorre erro.

Arquivos relacionados:

- `apps/api/src/utils/response.js`

Testes relacionados:

- Nenhum teste relacionado identificado.

### 8. Validação numérica possivelmente incompleta

- Arquivo: `apps/api/src/validators/job.js`
- Linha aproximada: 6
- Regra: `unsafe_numeric_range`
- Status: **strong_static_evidence**
- Proof score: **92.0**

Evidências:

- Campos mínimo e máximo estão presentes no mesmo fluxo.
- Nenhuma validação cruzada foi localizada.

Contraevidências:

- Sintaxe JavaScript válida.

Teste local sugerido:

- Validar payload com budgetMin maior que budgetMax e confirmar se o schema aceita a combinação inválida.

Arquivos relacionados:

- Nenhum import local relacionado encontrado.

Testes relacionados:

- Nenhum teste relacionado identificado.

### 9. Lógica de produção marcada como TODO/FIXME

- Arquivo: `apps/api/src/config/db.js`
- Linha aproximada: 2
- Regra: `todo_business_logic`
- Status: **strong_static_evidence**
- Proof score: **90.0**

Evidências:

- Marcadores encontrados: // TODO: wire Prisma client from @freelanceflow/db package
- Arquivo possui pouquíssimas linhas executáveis.

Contraevidências:

- Sintaxe JavaScript válida.

Teste local sugerido:

- Identificar qual rota ou serviço depende deste arquivo e executar o fluxo local para confirmar comportamento incompleto.

Arquivos relacionados:

- Nenhum import local relacionado encontrado.

Testes relacionados:

- Nenhum teste relacionado identificado.

### 10. Lógica de produção marcada como TODO/FIXME

- Arquivo: `apps/api/src/services/paymentService.js`
- Linha aproximada: 2
- Regra: `todo_business_logic`
- Status: **needs_runtime_reproduction**
- Proof score: **60.0**

Evidências:

- Marcadores encontrados: // TODO: integrate Stripe SDK and return client secret.

Contraevidências:

- O arquivo contém implementação além do TODO/FIXME.
- Sintaxe JavaScript válida.

Teste local sugerido:

- Identificar qual rota ou serviço depende deste arquivo e executar o fluxo local para confirmar comportamento incompleto.

Arquivos relacionados:

- Nenhum import local relacionado encontrado.

Testes relacionados:

- Nenhum teste relacionado identificado.

### 11. Lógica de produção marcada como TODO/FIXME

- Arquivo: `apps/api/src/services/searchService.js`
- Linha aproximada: 2
- Regra: `todo_business_logic`
- Status: **needs_runtime_reproduction**
- Proof score: **60.0**

Evidências:

- Marcadores encontrados: // TODO: use PostgreSQL full-text search + ranking.

Contraevidências:

- O arquivo contém implementação além do TODO/FIXME.
- Sintaxe JavaScript válida.

Teste local sugerido:

- Identificar qual rota ou serviço depende deste arquivo e executar o fluxo local para confirmar comportamento incompleto.

Arquivos relacionados:

- Nenhum import local relacionado encontrado.

Testes relacionados:

- Nenhum teste relacionado identificado.

### 12. Lógica de produção marcada como TODO/FIXME

- Arquivo: `apps/api/src/services/authService.js`
- Linha aproximada: 4
- Regra: `todo_business_logic`
- Status: **needs_runtime_reproduction**
- Proof score: **60.0**

Evidências:

- Marcadores encontrados: // TODO: persist new user via Prisma | // TODO: verify password hash against stored user record

Contraevidências:

- O arquivo contém implementação além do TODO/FIXME.
- Sintaxe JavaScript válida.

Teste local sugerido:

- Identificar qual rota ou serviço depende deste arquivo e executar o fluxo local para confirmar comportamento incompleto.

Arquivos relacionados:

- `apps/api/src/utils/jwt.js`

Testes relacionados:

- Nenhum teste relacionado identificado.

## Candidato recomendado para reprodução

- Hipótese: **Objeto req.body encaminhado sem seleção explícita**
- Arquivo: `apps/api/src/controllers/paymentController.js`
- Status: **strong_static_evidence**
- Proof score: **97.0**
- Teste sugerido: Enviar campo extra não documentado no payload e verificar se ele chega ao serviço ou persistência. O teste deve usar mocks locais e não chamar serviços externos.

## Próximo gate

Criar um teste isolado no workspace de prova. O teste precisa falhar no código atual de forma reproduzível. Nenhuma issue será criada antes disso.