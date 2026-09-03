# ADR-007 — Dataform for SQL transformations

## Status
Accepted

## Refinamentos
- **2026-09-03 — ADR-052:** para o incremento `MVP_WALKING_SKELETON` a transformação SQL usa
  BigQuery SQL direto, com os arquivos `.sql` já no formato Dataform; a adoção do Dataform
  fica para um incremento seguinte. ADR-052 **refina, não substitui** esta decisão.

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
### A. dbt Cloud
Alternativa considerada e descartada por não equilibrar adequadamente os drivers acima.

### B. Airflow SQL scripts
Alternativa considerada; pode ser válida em outro contexto, mas aumenta risco, acoplamento ou complexidade para este projeto.

### C. Dataform
Alternativa escolhida ou base para a decisão.

## Decisão
**Dataform.**

## Por que
GCP-native integration and lower platform sprawl for initial build.

## Consequências positivas
- comportamento mais explícito e testável;
- decisão documentada para novos desenvolvedores/agentes;
- redução de ambiguidade.

## Consequências negativas / custo aceito
dbt may be reconsidered for ecosystem/portability requirements.

## Verificação
A decisão deve aparecer em SPECs, testes, CI ou políticas de repositório quando aplicável.

## Quando reconsiderar
Reconsiderar quando métricas operacionais, requisitos legais, custo, escala ou limitações de plataforma demonstrarem que os decision drivers mudaram materialmente.
