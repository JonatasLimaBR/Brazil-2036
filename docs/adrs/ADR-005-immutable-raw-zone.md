# ADR-005 — Immutable raw zone

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
### A. Overwrite source files
Alternativa considerada e descartada por não equilibrar adequadamente os drivers acima.

### B. Keep only transformed data
Alternativa considerada; pode ser válida em outro contexto, mas aumenta risco, acoplamento ou complexidade para este projeto.

### C. Immutable object storage
Alternativa escolhida ou base para a decisão.

## Decisão
**Immutable object storage.**

## Por que
Audit/replay/provenance require original bytes.

## Consequências positivas
- comportamento mais explícito e testável;
- decisão documentada para novos desenvolvedores/agentes;
- redução de ambiguidade.

## Consequências negativas / custo aceito
Storage growth is accepted and managed by lifecycle policy.

## Verificação
A decisão deve aparecer em SPECs, testes, CI ou políticas de repositório quando aplicável.

## Quando reconsiderar
Reconsiderar quando métricas operacionais, requisitos legais, custo, escala ou limitações de plataforma demonstrarem que os decision drivers mudaram materialmente.
