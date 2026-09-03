# ADR-020 — Four-eyes for security-critical actions

## Status
Accepted

## Contexto
Esta decisão é parte do baseline arquitetural do BRASIL 2036 e deve ser lida com o `CONTEXTO.md`.

## Decision drivers
- segurança e auditabilidade;
- reprodutibilidade;
- escalabilidade;
- custo operacional;
- aderência ao GCP;
- clareza para portfólio e agentes de código.

## Alternativas consideradas
### A. Self approval
Alternativa considerada e descartada por não equilibrar adequadamente os drivers acima.

### B. Single admin approval
Alternativa considerada; pode ser válida em outro contexto, mas aumenta risco, acoplamento ou complexidade para este projeto.

### C. Requester and approver must differ
Alternativa escolhida ou base para a decisão.

## Decisão
**Requester and approver must differ.**

## Por que
Reduces insider/error risk.

## Consequências positivas
- comportamento mais explícito e testável;
- decisão documentada para novos desenvolvedores/agentes;
- redução de ambiguidade.

## Consequências negativas / custo aceito
Slower privileged operations.

## Verificação
A decisão deve aparecer em SPECs, testes, CI ou políticas de repositório quando aplicável.

## Quando reconsiderar
Reconsiderar quando métricas operacionais, requisitos legais, custo, escala ou limitações de plataforma demonstrarem que os decision drivers mudaram materialmente.
