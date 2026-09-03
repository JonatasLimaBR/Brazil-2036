# ADR-008 — dados.gov.br as discovery catalog

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
### A. Treat portal as warehouse
Alternativa considerada e descartada por não equilibrar adequadamente os drivers acima.

### B. Ignore portal and call agencies only
Alternativa considerada; pode ser válida em outro contexto, mas aumenta risco, acoplamento ou complexidade para este projeto.

### C. Use as discovery/catalog plus ingest resources
Alternativa escolhida ou base para a decisão.

## Decisão
**Use as discovery/catalog plus ingest resources.**

## Por que
Reflects how catalog metadata and underlying resources are actually published.

## Consequências positivas
- comportamento mais explícito e testável;
- decisão documentada para novos desenvolvedores/agentes;
- redução de ambiguidade.

## Consequências negativas / custo aceito
Connector layer must handle heterogeneous agency hosting.

## Verificação
A decisão deve aparecer em SPECs, testes, CI ou políticas de repositório quando aplicável.

## Quando reconsiderar
Reconsiderar quando métricas operacionais, requisitos legais, custo, escala ou limitações de plataforma demonstrarem que os decision drivers mudaram materialmente.
