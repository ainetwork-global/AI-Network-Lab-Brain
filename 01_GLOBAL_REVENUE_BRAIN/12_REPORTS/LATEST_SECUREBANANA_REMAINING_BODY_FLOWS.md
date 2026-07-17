# SecureBananaLabs — Remaining Body Flows

Gerado em: 2026-07-17T13:06:24.787341+00:00

## Objetivo

Determinar se o encaminhamento integral de `req.body` resulta em persistência irrestrita ou se os serviços selecionam campos explicitamente.

## Ranking

### 1. message

- Função: `sendMessage`
- Controller: `apps/api/src/controllers/messageController.js`
- Service: `apps/api/src/services/messageService.js`
- `req.body` encaminhado: **True**
- Seleção explícita de campos: **False**
- Campos usados: ``
- Persistência irrestrita: **True**
- Placeholder: **False**
- Risk score: **80**
- Decisão: **BUILD_TARGETED_RUNTIME_PROOF**
- Próxima ação: **mock_persistence_and_test_extra_field**

#### Service source

```javascript
const messages = [];

export async function listMessages() {
  return messages;
}

export async function sendMessage(payload) {
  const message = { id: `msg_${Date.now()}`, ...payload, sentAt: new Date().toISOString() };
  messages.push(message);
  return message;
}

```

### 2. notification

- Função: `createNotification`
- Controller: `apps/api/src/controllers/notificationController.js`
- Service: `apps/api/src/services/notificationService.js`
- `req.body` encaminhado: **True**
- Seleção explícita de campos: **False**
- Campos usados: ``
- Persistência irrestrita: **True**
- Placeholder: **False**
- Risk score: **80**
- Decisão: **BUILD_TARGETED_RUNTIME_PROOF**
- Próxima ação: **mock_persistence_and_test_extra_field**

#### Service source

```javascript
const notifications = [];

export async function listNotifications() {
  return notifications;
}

export async function createNotification(payload) {
  const notification = { id: `ntf_${Date.now()}`, read: false, ...payload };
  notifications.push(notification);
  return notification;
}

```

### 3. proposal

- Função: `createProposal`
- Controller: `apps/api/src/controllers/proposalController.js`
- Service: `apps/api/src/services/proposalService.js`
- `req.body` encaminhado: **True**
- Seleção explícita de campos: **False**
- Campos usados: ``
- Persistência irrestrita: **True**
- Placeholder: **False**
- Risk score: **80**
- Decisão: **BUILD_TARGETED_RUNTIME_PROOF**
- Próxima ação: **mock_persistence_and_test_extra_field**

#### Service source

```javascript
const proposals = [];

export async function listProposals() {
  return proposals;
}

export async function createProposal(payload) {
  const proposal = { id: `prp_${Date.now()}`, ...payload };
  proposals.push(proposal);
  return proposal;
}

```

### 4. review

- Função: `createReview`
- Controller: `apps/api/src/controllers/reviewController.js`
- Service: `apps/api/src/services/reviewService.js`
- `req.body` encaminhado: **True**
- Seleção explícita de campos: **False**
- Campos usados: ``
- Persistência irrestrita: **True**
- Placeholder: **False**
- Risk score: **80**
- Decisão: **BUILD_TARGETED_RUNTIME_PROOF**
- Próxima ação: **mock_persistence_and_test_extra_field**

#### Service source

```javascript
const reviews = [];

export async function listReviews() {
  return reviews;
}

export async function createReview(payload) {
  const review = { id: `rev_${Date.now()}`, ...payload };
  reviews.push(review);
  return review;
}

```

### 5. user

- Função: `createUser`
- Controller: `apps/api/src/controllers/userController.js`
- Service: `apps/api/src/services/userService.js`
- `req.body` encaminhado: **True**
- Seleção explícita de campos: **False**
- Campos usados: ``
- Persistência irrestrita: **True**
- Placeholder: **False**
- Risk score: **80**
- Decisão: **BUILD_TARGETED_RUNTIME_PROOF**
- Próxima ação: **mock_persistence_and_test_extra_field**

#### Service source

```javascript
const users = [];

export async function listUsers() {
  return users;
}

export async function createUser(payload) {
  const user = { id: `usr_${Date.now()}`, ...payload };
  users.push(user);
  return user;
}

```

## Candidato recomendado

- Fluxo: **message**
- Decisão: **BUILD_TARGETED_RUNTIME_PROOF**
- Risk score: **80**
- Próxima ação: **mock_persistence_and_test_extra_field**

## Segurança operacional

- Código original alterado: **não**
- Dependências instaladas: **não**
- Ação externa realizada: **não**
- Issue criada: **não**
- Comentário criado: **não**
- Fork criado: **não**
- Pull request criado: **não**