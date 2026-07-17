# SecureBananaLabs — Business Logic Hunter

Gerado em: 2026-07-17T17:38:28.2507724Z

## Resultado

- Decisão: **UNGUARDED_STATE_CANDIDATE_FOUND**
- Arquivos analisados: **44**
- Achados: **12**
- Candidatos financeiros: **0**
- Transições sem guarda: **2**
- State-machine candidates: **10**
- Próxima ação: **trace_highest_priority_state_candidate**

## Candidato recomendado

- Arquivo: `apps\api\src\services\notificationService.js`
- Linha: **8**
- Risk score: **80**
- Decisão: **UNGUARDED_STATE_TRANSITION_REVIEW**
- Linha analisada: `const notification = { id: `ntf_${Date.now()}`, read: false, ...payload };`

## Top 20

### 1. apps\api\src\services\notificationService.js:8

- Score: **80**
- Decisão: **UNGUARDED_STATE_TRANSITION_REVIEW**
- Controlado pela requisição: **True**
- Persistência detectada: **True**
- Estado anterior verificado: **False**
- Contexto financeiro: **False**

### 2. apps\api\src\services\jobService.js:8

- Score: **80**
- Decisão: **UNGUARDED_STATE_TRANSITION_REVIEW**
- Controlado pela requisição: **True**
- Persistência detectada: **True**
- Estado anterior verificado: **False**
- Contexto financeiro: **False**

### 3. apps\api\src\utils\response.js:1

- Score: **55**
- Decisão: **STATE_MACHINE_REVIEW_REQUIRED**
- Controlado pela requisição: **True**
- Persistência detectada: **False**
- Estado anterior verificado: **False**
- Contexto financeiro: **False**

### 4. apps\api\src\utils\response.js:5

- Score: **55**
- Decisão: **STATE_MACHINE_REVIEW_REQUIRED**
- Controlado pela requisição: **True**
- Persistência detectada: **False**
- Estado anterior verificado: **False**
- Contexto financeiro: **False**

### 5. apps\api\src\utils\response.js:6

- Score: **55**
- Decisão: **STATE_MACHINE_REVIEW_REQUIRED**
- Controlado pela requisição: **True**
- Persistência detectada: **False**
- Estado anterior verificado: **False**
- Contexto financeiro: **False**

### 6. apps\api\src\utils\response.js:2

- Score: **55**
- Decisão: **STATE_MACHINE_REVIEW_REQUIRED**
- Controlado pela requisição: **True**
- Persistência detectada: **False**
- Estado anterior verificado: **False**
- Contexto financeiro: **False**

### 7. apps\api\src\services\authService.js:17

- Score: **55**
- Decisão: **STATE_MACHINE_REVIEW_REQUIRED**
- Controlado pela requisição: **True**
- Persistência detectada: **False**
- Estado anterior verificado: **False**
- Contexto financeiro: **False**

### 8. apps\api\src\services\authService.js:9

- Score: **55**
- Decisão: **STATE_MACHINE_REVIEW_REQUIRED**
- Controlado pela requisição: **True**
- Persistência detectada: **False**
- Estado anterior verificado: **False**
- Contexto financeiro: **False**

### 9. apps\api\src\services\authService.js:8

- Score: **55**
- Decisão: **STATE_MACHINE_REVIEW_REQUIRED**
- Controlado pela requisição: **True**
- Persistência detectada: **False**
- Estado anterior verificado: **False**
- Contexto financeiro: **False**

### 10. apps\api\src\controllers\authController.js:20

- Score: **55**
- Decisão: **STATE_MACHINE_REVIEW_REQUIRED**
- Controlado pela requisição: **True**
- Persistência detectada: **False**
- Estado anterior verificado: **False**
- Contexto financeiro: **False**

### 11. apps\api\src\services\authService.js:22

- Score: **55**
- Decisão: **STATE_MACHINE_REVIEW_REQUIRED**
- Controlado pela requisição: **True**
- Persistência detectada: **False**
- Estado anterior verificado: **False**
- Contexto financeiro: **False**

### 12. apps\api\src\tests\health.test.js:18

- Score: **45**
- Decisão: **STATE_MACHINE_REVIEW_REQUIRED**
- Controlado pela requisição: **True**
- Persistência detectada: **False**
- Estado anterior verificado: **False**
- Contexto financeiro: **False**

## Segurança

- Código analisado alterado: **não**
- Requisição externa executada: **não**
- Issue criada: **não**
- Pull request criado: **não**
