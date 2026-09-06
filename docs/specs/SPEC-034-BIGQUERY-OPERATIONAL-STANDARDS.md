# SPEC-034 — BigQuery Operational Standards

Padrão operacional transversal (não ligado a 1 domínio de produto — mesmo papel que `SPEC-031`
cumpre para CI): como toda tabela e toda query BigQuery deste projeto DEVE ser construída e
operada. Extraído do padrão já em uso pelas 3 fatias existentes (dívida, INSS, fiscal), não
inventado — ver `ADR-052`, `ADR-055`, `ADR-056`, `ADR-057`.

## 1. Cap de custo por query (Realization: `ADR-057`)

Toda query de transformação (Silver/Gold, `registry`, `provenance`) e toda leitura da API DEVE
ter `maximum_bytes_billed` definido. `ingestion/src/ingestion/bigquery_io.py::run_sql()` e
`api/src/api/bigquery_repo.py::build_bigquery_run_query()` aplicam **1 GiB
(`DEFAULT_MAX_BYTES_BILLED = 1_073_741_824`) por padrão** — generoso para as tabelas do projeto
hoje (a maior, INSS Indeferidos, tem ~15 mil linhas), mas suficiente para pegar um erro grosseiro
(ex.: `JOIN` sem filtro de partição) antes que vire custo real.

**Exceção deliberada — `LOAD DATA`:** carga em lote (`LOAD DATA OVERWRITE ... FROM FILES(...)`,
usada por `bronze.load()`/`bronze.load_partition()`) é billada pelo BigQuery como carga (grátis),
não como bytes processados — aplicar o cap aqui é um controle desalinhado, e pode quebrar a carga
de um arquivo-fonte legitimamente grande (já visto na casa de 7+ GB, INSS Emitidos). Toda chamada
`run_sql`/`scalar` dentro de `bronze.py` passa `maximum_bytes_billed=None` explicitamente.

**Nota sobre tabelas clusterizadas:** a estimativa de bytes do BigQuery para uma tabela
clusterizada (toda tabela deste projeto é, ver §2) é um *upper bound* — pode superestimar o custo
real. O cap de 1 GiB tem margem suficiente para isso não gerar falso-positivo nas tabelas atuais.

Uma fatia futura com volume real de GB numa consulta de transformação/leitura deve passar
`maximum_bytes_billed` explicitamente maior naquele ponto de chamada — nunca subir o default
global sem justificativa medida.

## 2. Particionamento e clustering (norma obrigatória)

Toda tabela Silver/Gold nova DEVE:
- `PARTITION BY` um campo de data de referência (`reference_date`, ou equivalente truncado ao
  grão da tabela).
- `CLUSTER BY` a(s) chave(s) de negócio mais usada(s) em filtro/agrupamento.

Precedente real (não teórico): `gold_debt_state_current` (`PARTITION BY reference_date CLUSTER BY
state_ibge_code`), `gold_inss_beneficios_*` (idem + `especie_codigo`), `gold_fiscal_uniao`
(idem + `metric_id`). Revisão de PR deve rejeitar uma tabela Silver/Gold nova sem essas cláusulas,
salvo justificativa explícita registrada em ADR.

## 3. Retenção / lifecycle por camada

| Camada | Política | Motivo |
|---|---|---|
| RAW (GCS) | Imutável, retida indefinidamente | Registro de auditoria da cadeia de proveniência (`SPEC-007`) — nunca expirado automaticamente. `infra/terraform/storage.tf` já limpa versões `ARCHIVED` antigas do objeto (não o dado RAW corrente). |
| Bronze / Silver (BigQuery) | Sem TTL implementado nesta fatia | Recomputáveis a partir de RAW a qualquer momento; sem pressão de custo real hoje que justifique a engenharia de um TTL automático (YAGNI). Revisar quando o volume de armazenamento justificar. |
| Gold / `metric_provenance` (BigQuery) | Sem TTL | É o produto público-facing em si. |
| Datasets `citest_*` (CI) | TTL de 1h (`default_table_expiration_ms`), já implementado desde `CI_ASSURANCE_GATES` | Sem mudança nesta fatia. |

## 4. Fora de escopo (deliberado)

- Dashboards de custo (billing export, cost/source/module/model) — `EPIC-042`, feature de produto.
- Enforcement automático via lint de CI (`sqlfluff` ou similar checando `PARTITION BY` em toda SQL nova) — sem ferramenta integrada ao `ci.yml` hoje.
- Orçamento de projeto / alertas de billing GCP — infraestrutura (Terraform), mais amplo que o cap por query.
- Automação de delete além do já existente em `storage.tf`.
- SPEC/ADR de MLOps/LLMOps/AgentOps — sem modelo/agente em produção ainda (`EPIC-020`/`EPIC-026`/`EPIC-043`).

## 5. Verificação

`ingestion/tests/test_bigquery_io.py`, `test_bronze_partition.py`
(`test_load_has_no_bytes_billed_cap`, `test_load_partition_has_no_bytes_billed_cap`),
`api/tests/test_bigquery_repo.py::test_build_bigquery_run_query_applies_cost_cap`. Gate
`integration` do `ci.yml` (já roda os 3 pipelines reais contra BigQuery) confirma que o cap não
quebra nenhuma query real do projeto.
