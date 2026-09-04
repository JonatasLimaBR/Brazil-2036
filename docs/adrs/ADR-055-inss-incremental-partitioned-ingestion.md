# ADR-055 — Backfill resumível + escrita por partição para datasets multi-recurso

## Status
Accepted

## Contexto
Esta decisão é parte do baseline arquitetural do BRASIL 2036 e deve ser lida com o `CONTEXTO.md`.
O `MVP_WALKING_SKELETON` provou o padrão RAW→Bronze→Silver→Gold→provenance contra 1 dataset
(Dívida Consolidada) publicado como **1 arquivo com todo o histórico**. `pipeline.run()`
reescreve a tabela inteira (`CREATE OR REPLACE TABLE`) a cada execução — correto ali, porque
não há histórico a preservar entre runs.

`INSS_BENEFICIOS` (fatia #2) ingere 3 datasets publicados como **1 recurso por mês** (37–108
recursos cada, em `dadosabertos.inss.gov.br`), com pedido explícito de ingerir o máximo de
histórico disponível. Reescrever a tabela inteira a cada mês apagaria os meses já carregados
nos runs anteriores.

A descoberta real também expôs um risco pré-existente: `registry.upsert_dataset_registry()` e
`provenance.write_from_gold()` faziam `CREATE OR REPLACE TABLE` em **tabelas compartilhadas**
(`dataset_registry`, `metric_provenance`) — corretas com 1 dataset, mas destrutivas assim que um
segundo dataset chamasse essas funções (apagaria a linha/os dados do primeiro).

## Decision drivers
- integridade de dados já em produção (dívida consolidada);
- idempotência e capacidade de retomar um backfill interrompido;
- reaproveitar o máximo de código já testado, sem reescrever o pipeline do zero;
- custo/tempo de execução do backfill (centenas de GB reais).

## Alternativas consideradas
### A. Mudar `discover()`/`pipeline.run()` para iterar internamente sobre N recursos
Considerada e descartada: muda a assinatura de uma função já testada e em produção
(`pipeline.run()`, usada pela dívida); qualquer regressão ali afeta o dataset já shipado.

### B. Reescrever a tabela inteira a cada mês, aceitando reprocessar tudo
Considerada e descartada: inviável em tempo/custo com 37–108 recursos por dataset.

### C. Orquestrador externo (`backfill.py`) + escrita por partição, `pipeline.run()` preservado
Alternativa escolhida.

## Decisão
- **`registry.upsert_dataset_registry()`** passa a fazer `MERGE` escopado por `dataset_id`
  (antes: `CREATE OR REPLACE TABLE` reescrevendo a tabela inteira).
- **`provenance.write_from_gold()`** passa a fazer `DELETE`+`INSERT` escopado por
  `(metric_id, reference_date)` (antes: `CREATE OR REPLACE TABLE` reescrevendo a tabela
  inteira); ganha os parâmetros `metric_id` e `reference_date` (substitui `reference_year`).
- Um novo módulo **`ingestion/src/ingestion/ckan.py`** lista recursos reais via
  `package_show` do portal CKAN da agência de origem — nunca constrói URL por convenção de
  nome (a convenção de nome do INSS mudou no meio da janela de dados, provado ao vivo).
- Um novo módulo **`ingestion/src/ingestion/backfill.py`** itera sobre a lista de recursos,
  pula os já carregados (checagem via `INFORMATION_SCHEMA.PARTITIONS` do Bronze), e chama
  `pipeline.run()` (dívida, inalterado) ou uma nova função de pipeline com escrita por partição
  (INSS) uma vez por recurso — resumível: uma execução interrompida retoma sem reprocessar.
- Bronze/Silver/Gold do INSS usam `LOAD DATA OVERWRITE <table>$<YYYYMM>` (decorador de
  partição) e `DELETE`+`INSERT` escopado ao mês, em vez de `CREATE OR REPLACE TABLE` cheio.
  A dívida mantém seu `CREATE OR REPLACE TABLE` (correto para 1 arquivo com todo o histórico).

## Por que
Reaproveita 100% do pipeline já provado sem arriscar sua assinatura pública; corrige um risco
real de perda de dado em produção que só se manifestaria ao adicionar um segundo dataset;
particionamento por mês torna o backfill idempotente e seguro de reexecutar.

## Consequências positivas
- `dataset_registry` e `metric_provenance` agora suportam múltiplos datasets/métricas sem se
  destruírem mutuamente — corrige um risco que existia desde o `MVP_WALKING_SKELETON`, mas só
  seria acionado ao adicionar um segundo dataset.
- Backfill resumível: falha num mês não obriga reprocessar os demais.
- `ckan.py` é genérico — reutilizável para qualquer fonte CKAN futura (Tesouro, IBGE etc.).

## Consequências negativas / custo aceito
- `provenance.write_from_gold()` muda de assinatura pública (`reference_year` → `metric_id` +
  `reference_date`) — 1 ponto de chamada (`pipeline.py`) e os testes de `test_provenance.py`
  precisaram ser atualizados.
- Backfill de ~183 recursos ao todo é uma execução longa (dezenas/centenas de GB); tempo real
  medido e reportado no `BUILD_REPORT` de `INSS_BENEFICIOS`.

## Verificação
`ingestion/tests/test_registry.py`, `test_provenance.py`, `test_pipeline.py`,
`test_ckan.py`, `test_backfill.py`; gate `integration` do `ci.yml` contra pelo menos 1 dos 3
datasets INSS via fixture.

## Quando reconsiderar
Se um dataset futuro precisar de grão sub-mensal (diário/semanal), o decorador de partição e o
escopo de `reference_date` precisam generalizar além de `YYYYMM`.
