# ADR-016 — Monte Carlo percentiles

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
### A. Single deterministic scenario
Alternativa considerada e descartada por não equilibrar adequadamente os drivers acima.

### B. LLM uncertainty wording
Alternativa considerada; pode ser válida em outro contexto, mas aumenta risco, acoplamento ou complexidade para este projeto.

### C. Explicit distributions and percentiles
Alternativa escolhida ou base para a decisão.

## Decisão
**Explicit distributions and percentiles.**

## Por que
Quantifies uncertainty reproducibly.

## Consequências positivas
- comportamento mais explícito e testável;
- decisão documentada para novos desenvolvedores/agentes;
- redução de ambiguidade.

## Consequências negativas / custo aceito
Assumptions about distributions must be documented.

## Verificação
A decisão deve aparecer em SPECs, testes, CI ou políticas de repositório quando aplicável.

## Quando reconsiderar
Reconsiderar quando métricas operacionais, requisitos legais, custo, escala ou limitações de plataforma demonstrarem que os decision drivers mudaram materialmente.
