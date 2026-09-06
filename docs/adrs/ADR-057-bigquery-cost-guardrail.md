# ADR-057 — Cap de custo por query via `maximum_bytes_billed`, exceto `LOAD DATA`

## Status
Accepted

## Contexto
Esta decisão é parte do baseline arquitetural do BRASIL 2036 e deve ser lida com o `CONTEXTO.md`.
Desde `CI_ASSURANCE_GATES` (`SHIPPED §7`), um achado residual ficou rastreado e nunca fechado:
nenhuma query de produção (`ingestion/src/ingestion/bigquery_io.py::run_sql()`,
`api/src/api/bigquery_repo.py::build_bigquery_run_query()`) tem `maximum_bytes_billed` — o
projeto não tinha nenhuma barreira técnica contra uma query malformada (ex.: `JOIN` sem filtro de
partição varrendo uma tabela inteira) virar custo real, só disciplina de code review. `R-012` no
Risk Register ("Custo GCP sem controle") documentava o risco sem controle correspondente
implementado para essa parte específica.

Pedido explícito do usuário ao final da fatia `FISCAL_RECEITA_DESPESA`: confirmar práticas de
FinOps/DataOps e, se ausentes, formalizá-las (`SPEC-034` cobre a norma; este ADR formaliza a
decisão de código).

Pesquisa real sobre o comportamento de billing do BigQuery (não suposição, ver
`DESIGN_BIGQUERY_OPERATIONAL_STANDARDS.md §0`): "batch loading data... is free" — `LOAD DATA
OVERWRITE ... FROM FILES(...)` (usado por `bronze.load()`/`bronze.load_partition()`) é billado
como carga, não como bytes processados. Um arquivo-fonte real já apareceu na casa de 7+ GB (INSS
Emitidos, sessão de `INSS_BENEFICIOS`). Aplicar um cap de bytes-processados a uma operação de
carga é um controle desalinhado com o que ela realmente cobra, e arriscaria falso-positivo numa
carga legítima e grande.

## Decision drivers
- fechar o achado residual `R-012` de verdade, não só no papel;
- não quebrar nenhuma query real das 3 fatias já em produção (dívida, INSS, fiscal);
- não aplicar um controle de custo onde ele é estruturalmente desalinhado com o billing real.

## Alternativas consideradas
### A. Cap único, sem exceção, aplicado a toda chamada `run_sql`/`scalar` incluindo `LOAD DATA`
Considerada e descartada: arriscaria quebrar uma carga real e grande (já visto: 7+ GB), e o
comportamento de billing real de `LOAD DATA` (carga grátis) torna o cap um controle sem
correspondência real ali.

### B. Cap mais restritivo (100 MB)
Considerada e descartada por decisão do usuário no Brainstorm: mais restritivo do que o
necessário — todas as tabelas do projeto hoje são pequenas (a maior, INSS Indeferidos, ~15 mil
linhas), e tabelas clusterizadas (todas, `SPEC-034 §2`) têm estimativa de bytes conservadora
(*upper bound*), o que aumenta o risco de falso-positivo com um cap mais apertado.

### C. Cap de 1 GiB por padrão, com opt-out explícito (`maximum_bytes_billed=None`) para as
chamadas internas de `bronze.py`
Alternativa escolhida.

## Decisão
- **`ingestion/src/ingestion/bigquery_io.py`**: `DEFAULT_MAX_BYTES_BILLED = 1_073_741_824` (1
  GiB). `run_sql()`/`scalar()` ganham `maximum_bytes_billed: int | None =
  DEFAULT_MAX_BYTES_BILLED` — aditivo, nenhum caller existente precisa mudar.
- **`ingestion/src/ingestion/bronze.py`**: toda chamada `run_sql`/`scalar` dentro de `load()` e
  `load_partition()` passa `maximum_bytes_billed=None` explicitamente — cobre `LOAD DATA` e as
  demais etapas da mesma função (a `CREATE OR REPLACE`/`INSERT INTO ... FROM staging` seguinte,
  e o `SELECT COUNT(*)` de confirmação, para não deixar o cap ativo só em parte do fluxo de uma
  carga potencialmente grande).
- **`api/src/api/bigquery_repo.py::build_bigquery_run_query()`**: mesmo valor
  (`DEFAULT_MAX_BYTES_BILLED = 1_073_741_824`), definido localmente (não importado de
  `ingestion/` — pacotes independentes, sem biblioteca compartilhada hoje), adicionado ao
  `QueryJobConfig` que a função já construía para `query_parameters`.

## Por que
Fecha o gap de código real do `R-012` sem inventar um número de cap sem embasamento (1 GiB é
generoso o bastante para as tabelas reais do projeto, mesmo com a superestimativa de clustering);
a exceção para `LOAD DATA` é justificada por pesquisa real sobre o billing do BigQuery, não por
conveniência — aplicar o cap ali seria um controle correto na forma, errado na substância.

## Consequências positivas
- Toda consulta de transformação e leitura de produção agora tem uma rede de segurança real
  contra erro grosseiro de custo, sem exigir mudança de comportamento de nenhum caller existente.
- `R-012` no `RISK-CONTROL-TEST-MATRIX.md` passa a refletir um controle real implementado
  (distinto do orçamento de projeto/billing export, que continua em aberto, declarado como tal).
- `bigquery_io.py::BigQueryClient` (Protocol) e `_fakes.py::FakeBigQuery` ganham suporte a
  `job_config` de forma genérica — qualquer teste futuro pode inspecionar o cap aplicado.

## Consequências negativas / custo aceito
- O valor `1_073_741_824` existe duplicado em 2 arquivos (`ingestion/`, `api/`) — aceito
  conscientemente (D2 do DESIGN) para não introduzir uma dependência entre pacotes independentes
  por causa de 1 constante.
- `bronze.py` fica sem essa rede de segurança específica — mitigado porque `LOAD DATA` é
  estruturalmente diferente (carrega o arquivo inteiro por design, não "vaza" por engano de JOIN
  como uma consulta de transformação vazaria).

## Verificação
`ingestion/tests/test_bigquery_io.py` (cap por padrão, `None` desliga, valor customizado),
`ingestion/tests/test_bronze_partition.py::test_load_has_no_bytes_billed_cap` e
`test_load_partition_has_no_bytes_billed_cap` (regressão do opt-out),
`api/tests/test_bigquery_repo.py::test_build_bigquery_run_query_applies_cost_cap` (mock real de
`bigquery.Client`, confirma o `job_config` construído). Gate `integration` do `ci.yml` confirma
que nenhuma query real das 3 fatias quebra com o cap ativo.

## Quando reconsiderar
Se uma fatia futura precisar legitimamente de mais de 1 GiB numa consulta de transformação ou
leitura (não de carga), o ponto de chamada específico deve passar `maximum_bytes_billed` maior —
nunca subir o default global sem uma medição real do volume que o justifique.
