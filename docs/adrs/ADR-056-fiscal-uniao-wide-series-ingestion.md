# ADR-056 — Ingestão de série larga recomputada por run (Fiscal & DebtLab)

## Status
Accepted

## Contexto
Esta decisão é parte do baseline arquitetural do BRASIL 2036 e deve ser lida com o `CONTEXTO.md`.
`MVP_WALKING_SKELETON` provou o padrão contra 1 dataset publicado como **1 arquivo com todo o
histórico, nunca reescrito** (dívida). `INSS_BENEFICIOS` (`ADR-055`) provou o padrão contra
datasets publicados como **1 recurso novo por período**, imutável, exigindo escrita por partição
e backfill resumível.

`FISCAL_RECEITA_DESPESA` (fatia #3) descobriu, ao baixar e abrir o arquivo real (não suposição),
uma terceira forma de publicação: o dataset "Resultado do Tesouro Nacional — Série Histórica"
(Tesouro Transparente/CKAN) republica **as 356 colunas mensais inteiras (1997–2026) no mesmo
objeto todo mês** — nem um arquivo imutável por período (INSS), nem um único arquivo que nunca
muda (dívida). A mesma tabela larga também contém, na mesma linha-grão, receita líquida, despesa
total e resultado primário já calculado pela fonte — 3 métricas de 1 arquivo, não 3 datasets
distintos.

A descoberta real também expôs 2 riscos que o mecanismo existente não cobria:
1. `contract.check_gold_period()` rejeitava incondicionalmente qualquer valor negativo — mas
   135 dos 356 meses reais (38%) de resultado primário são negativos (déficit), incluindo meses
   recentes (2025-11 a 2026-06 no arquivo inspecionado).
2. `bronze.load()` (usado pela dívida) tinha as colunas `UF, ANO, VALOR` e o delimitador `;`
   hardcoded no corpo da função — nenhum outro dataset poderia reusá-la sem esses nomes exatos.

## Decision drivers
- fidelidade ao dado real: a fonte já publica o resultado primário oficial, calculado por ela —
  não fabricar um recálculo nosso que possa divergir por ajustes metodológicos;
- reaproveitar o máximo de mecanismo já provado (`registry`, `bronze`, `provenance`, `contract`)
  sem quebrar os 2 datasets que já o usam em produção;
- não deixar um déficit fiscal real (evento comum na história econômica) ser tratado como erro
  de parsing.

## Alternativas consideradas
### A. Forçar em `pipeline_incremental.py`, chamando `run()` 356 vezes (1 por mês)
Descartada: o `Connector` de `pipeline_incremental` assume "1 chamada = baixa 1 recurso novo";
aqui 1 único download já contém as 356 colunas — rodar 356 vezes baixaria o mesmo arquivo de
4,3 MB 356 vezes à toa, e não há "mês novo" a discriminar por recurso.

### B. 3 tabelas Gold separadas (seguir a decisão do DEFINE ao pé da letra)
Descartada após a descoberta real: receita, despesa e primário vêm do mesmo arquivo, mesmo grão,
mesmo pipeline — ao contrário do INSS (3 arquivos/schemas genuinamente distintos), fundir aqui
não confunde a métrica e evita 2 SQL/contratos a mais sem ganho de isolamento.

### C. Novo módulo `pipeline_wide_series.py` + `allow_negative` em `check_gold_period` + `columns`/`field_delimiter` em `bronze.load()`
Alternativa escolhida.

## Decisão
- Um novo módulo **`ingestion/src/ingestion/pipeline_wide_series.py`** processa "1 download =
  série larga completa, recomputada inteira a cada execução": baixa 1x, grava o artefato
  original em RAW sem modificação, grava a pivot longa derivada como um 2º objeto RAW separado
  (Bronze carrega dela), reescreve Bronze como tabela inteira (`CREATE OR REPLACE`, seguro aqui —
  tabela exclusiva do dataset), e reescreve Gold/provenance por `metric_id` inteiro a cada run.
- **`bronze.load()`** ganha `columns: Sequence[str]` e `field_delimiter: str`, com default
  igual ao shape original hardcoded da dívida (`UF, ANO, VALOR`, `;`) — comportamento inalterado
  para o caller existente.
- **`provenance.write_from_gold()`** ganha `reference_date: dt.date | None` — `None` amplia o
  escopo do `DELETE`+`INSERT` para `metric_id` inteiro, sem filtro de data, para uma fonte que
  recomputa todo o histórico a cada run.
- **`contract.check_gold_period()`** ganha `allow_negative: bool = False` — o pipeline passa
  `True` só para `fiscal_primario` (receita/despesa continuam protegidas contra negativo real).
- O Gold (`gold_fiscal_uniao`) inclui um `state_ibge_code` constante `'BR'` — sem dimensão
  territorial real nesta fonte, mantido só para que `provenance.write_from_gold()` (que seleciona
  essa coluna) e o formato de chave de `check_gold_period` não precisem de um caminho especial.

## Por que
Cada módulo de pipeline continua simples e correto para a forma de dado que resolve, em vez de
uma abstração forçada cobrindo 3 formas de publicação incompatíveis; os 2 pipelines existentes
(`pipeline.py`, `pipeline_incremental.py`) permanecem intocados, sem risco de regressão nas 2
fatias já em produção; o achado do resultado primário negativo é corrigido antes do primeiro
backfill real, não depois de um mês de déficit falhar em produção.

## Consequências positivas
- Terceira aplicação do padrão RAW→Bronze→Silver→Gold→provenance prova que ele generaliza a uma
  3ª forma de publicação sem reescrever o que já funciona.
- `bronze.load()` deixa de estar hardcoded a um único dataset — reutilizável por qualquer fonte
  futura publicada como "1 arquivo com todo o histórico" e schema de colunas diferente.
- `check_gold_period(allow_negative=...)` é reutilizável por qualquer métrica futura legitimamente
  negativa (ex.: resultado fiscal de qualquer nível de governo), não só esta.

## Consequências negativas / custo aceito
- `provenance.write_from_gold()` muda de assinatura pública (`reference_date` vira opcional) —
  2 pontos de chamada existentes (dívida, INSS) continuam passando uma data real e não mudam de
  comportamento, verificado por teste de regressão explícito.
- `state_ibge_code = 'BR'` é um sentinel sem significado territorial real — documentado no
  contrato de dados para não ser confundido com uma UF de verdade.

## Verificação
`ingestion/tests/test_contract.py`, `test_provenance.py`, `test_bronze_partition.py`,
`test_fiscal_uniao_connector.py`, `test_pipeline_wide_series.py`; gate `integration` do `ci.yml`
contra BigQuery real com fixture de 2 meses (1 superávit, 1 déficit — prova `allow_negative` ao
vivo, não só contra um cliente fake).

## Quando reconsiderar
Se uma fatia futura precisar de uma métrica derivada que a fonte NÃO publica pronta (ao contrário
do resultado primário aqui), a decisão de "nunca recalcular, sempre ingerir o valor publicado"
(DESIGN D5 de `FISCAL_RECEITA_DESPESA`) precisa ser revisitada caso a caso.
