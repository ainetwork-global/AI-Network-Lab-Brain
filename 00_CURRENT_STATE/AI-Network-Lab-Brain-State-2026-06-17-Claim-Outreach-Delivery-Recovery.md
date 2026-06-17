# AI Network Lab - Claim Outreach Delivery Recovery - 2026-06-17

## Estado validado

O projeto continua 100% cloud em Supabase.

O Claim Portal foi atualizado e publicado no repositório ainetwork-global.github.io.

A instrumentação nova do claim.html foi adicionada, mas ainda não há eventos granulares suficientes para análise.

## Métricas atuais

claim_invitation_created = 158
claim_page_view = 111
claim_started = 6
claim_completed = 1

## Diagnóstico

O gargalo real encontrado foi na fila github_claim_outreach_queue.

Antes da intervenção:

P1 pending = 31
P1 processing = 8
P1 sent = 3
P2 pending null = 114
P2 sent = 4

Os 8 processing estão órfãos desde 2026-06-08, com sent_at null, failed_at null e last_error null.

## Ação executada

Como o projeto é cloud-only e o Supabase Web Editor/Deploy apresentou erro Failed to fetch api.supabase.com, o worker foi simulado com segurança via SQL usando funções já existentes:

claim_next_github_outreach_batch()
mark_github_outreach_sent()

Foram processados 15 registros P1 em modo manual SQL cloud run.

Depois da intervenção:

P1 pending = 16
P1 processing = 8
P1 sent = 18
P2 pending null = 114
P2 sent = 4

## Conclusão

As funções SQL da fila funcionam.
A fila pending -> sent funciona.
O delivery target é gerado.
O gargalo não é mais estrutura de dados.
O gargalo é execução automática/scheduler do worker cloud.

## Próximo passo

Não excluir Edge Function.

Resolver com calma o problema de deploy do Supabase Web Editor ou criar caminho cloud seguro para invocação recorrente.

Prioridade imediata:
1. Não deletar github-claim-outreach-worker.
2. Não alterar secrets antigos.
3. Processar ou liberar os 8 processing órfãos.
4. Definir scheduler/invocação automática para consumir P1 pending.
