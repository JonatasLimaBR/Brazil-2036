# ADR-001 — GCP as primary cloud

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
### A. Multi-cloud from day one
Alternativa considerada e descartada por não equilibrar adequadamente os drivers acima.

### B. AWS-first
Alternativa considerada; pode ser válida em outro contexto, mas aumenta risco, acoplamento ou complexidade para este projeto.

### C. GCP-first
Alternativa escolhida ou base para a decisão.

## Decisão
**GCP-first.**

## Por que
The challenge/project is GCP-oriented; BigQuery/Vertex/Cloud Run form a coherent stack; multi-cloud now adds operational surface.

## Consequências positivas
- comportamento mais explícito e testável;
- decisão documentada para novos desenvolvedores/agentes;
- redução de ambiguidade.

## Consequências negativas / custo aceito
Accept initial provider concentration; preserve API/service boundaries.

## Verificação
A decisão deve aparecer em SPECs, testes, CI ou políticas de repositório quando aplicável.

## Quando reconsiderar
Reconsiderar quando métricas operacionais, requisitos legais, custo, escala ou limitações de plataforma demonstrarem que os decision drivers mudaram materialmente.
