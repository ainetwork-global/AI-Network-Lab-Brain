# Anti-Regression Rules — AI Network Lab

AI Network Lab NÃO está em estágio inicial.

O sistema já opera em produção.

Nunca:

- reconstruir Stripe do zero
- simplificar runtime já validado
- remover billing worker
- reestruturar Brain sem necessidade
- substituir arquitetura Supabase atual
- reiniciar onboarding flow
- sugerir MVP simplificado
- ignorar o estado salvo no cérebro
- repetir comandos antigos sem verificar o estágio atual

Sempre continuar a partir do estado atual.

Arquitetura já validada:

capture
-> onboarding
-> runtime
-> credits
-> scarcity
-> economic signal
-> Stripe LIVE
-> billing pipeline

Ajuda futura deve focar em:

- continuação
- observabilidade
- escala
- monetização
- autonomia econômica
- conversion rate
- authorization bottlenecks
- economic_authorized agents
