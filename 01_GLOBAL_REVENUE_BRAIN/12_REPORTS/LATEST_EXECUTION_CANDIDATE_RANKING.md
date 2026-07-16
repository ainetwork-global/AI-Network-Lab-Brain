# EXECUTION CANDIDATE RANKING

CURRENT_BEST_TARGET

O Brain deverá manter apenas uma oportunidade como prioridade máxima.

Critérios:

1. Probabilidade real de pagamento
2. Evidências verificadas
3. Valor esperado
4. Valor por hora
5. Complexidade técnica
6. Tempo estimado até receber
7. Facilidade de submissão
8. Necessidade de aprovação humana
9. Histórico do contratante
10. Histórico aprendido pelo Brain

Sempre que novas oportunidades forem descobertas:

- recalcular toda a fila;
- atualizar o ranking;
- substituir o CURRENT_BEST_TARGET quando existir opção melhor;
- nunca perder o histórico.

Resultado esperado:

CURRENT_BEST_TARGET
TOP 10
TOP 50
TOP 100

A fila deverá permanecer dinâmica.
