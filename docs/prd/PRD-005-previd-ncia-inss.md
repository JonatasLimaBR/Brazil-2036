# PRD-005 — Previdência & INSS

## 1. Problema
A sustentabilidade previdenciária precisa ser analisada de forma integrada com demografia, emprego e fiscal.

## 2. Públicos / stakeholders
Consultar `docs/discovery/01-USER-JOURNEYS.md`; o PRD deve ser lido no contexto das personas afetadas.

## 3. Resultado desejado
Entregar uma experiência mensurável que resolva o problema sem transferir decisões críticas ao LLM.

## 4. Escopo V1
- benefícios emitidos/mantidos/indeferidos
- territorialidade
- demografia
- receita/despesa
- projeção RGPS
- simulador previdenciário

## 5. Fora de escopo V1
- cancelar/conceder benefício
- classificar cidadão como fraudador
- usar microdado restrito sem base legal

## 6. Requisitos de confiança
- Provenance quando houver dado oficial.
- Observado, estimado e simulado visualmente distintos.
- Regras críticas aplicadas por arquitetura, não por prompt.
- Ações irreversíveis seguem approval workflow.
- Auditoria preservada.

## 7. Métricas de sucesso
- todas as saídas agregadas rastreáveis
- simulação reproduzível
- nenhuma capability punitiva no agente

## 8. Riscos
Consultar Risk Register e a matriz Risk → Control → Test. Novos riscos devem ser registrados antes do merge.

## 9. Dependências
Open Data Hub, Semantic Layer, Authorization, Provenance, Observability e serviços de domínio aplicáveis.

## 10. Critérios de aceite do produto
- Jornada principal pode ser concluída sem operação manual oculta.
- Dados/estimativas exibem origem e classificação.
- Falhas críticas são observáveis.
- Itens explicitamente fora do escopo não são adicionados por conveniência técnica.

## 11. Questões abertas
Devem ser resolvidas por ADR/SPEC quando alterarem arquitetura ou comportamento.
