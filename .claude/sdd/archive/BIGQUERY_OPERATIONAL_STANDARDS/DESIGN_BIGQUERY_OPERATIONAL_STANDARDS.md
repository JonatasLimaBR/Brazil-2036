# DESIGN — BIGQUERY_OPERATIONAL_STANDARDS

## Metadados

- **Feature:** BIGQUERY_OPERATIONAL_STANDARDS
- **Status:** ✅ Shipped
- **Fase:** 2 (Design)
- **Entrada:** `.claude/sdd/features/DEFINE_BIGQUERY_OPERATIONAL_STANDARDS.md` (Clarity 13/15)
- **Criado:** 2026-09-06
- **Idioma:** PT-BR
- **Branch:** a criar — `chore/bigquery-operational-standards`
- **Confiança:** 0.85 — sem `kb/` do plugin; padrões extraídos do código real já existente (3
  pares Silver/Gold, `bigquery_io.py`, `bigquery_repo.py`) + pesquisa real sobre o comportamento
  de billing do BigQuery (não suposição).
- **Próximo passo:** `/build .claude/sdd/features/DESIGN_BIGQUERY_OPERATIONAL_STANDARDS.md`

> Nota: assets do plugin SDD ausentes — documento segue a lista de seções do skill `sdd-design`.

---

## 0. Descoberta real (tarefa 1 — resolve OQ1–OQ3 do DEFINE)

Diferente de uma feature de ingestão, aqui a "descoberta real" é sobre o **comportamento de
billing do próprio BigQuery**, não sobre uma fonte de dado externa. Pesquisado via documentação
oficial do Google Cloud (não suposto):

- **OQ1 (LOAD DATA vs. SELECT) — resolvida.** "Batch loading data from Cloud Storage or local
  files into BigQuery is free" (exceto transferência de dados cross-region). `LOAD DATA OVERWRITE
  ... FROM FILES(...)` — usado por `bronze.load()`/`bronze.load_partition()` — é uma operação de
  carga em lote, billada como carga (grátis), não como bytes processados de uma consulta. Aplicar
  `maximum_bytes_billed` a esse tipo de statement é um controle **desalinhado** com o que ele
  realmente cobra — e pior, arriscaria quebrar cargas de arquivo-fonte legitimamente grandes (a
  sessão do `INSS_BENEFICIOS` já enfrentou um arquivo real de 7+ GB do Emitidos). **Decisão (D3
  abaixo): o cap não se aplica às chamadas internas de `bronze.py` que fazem `LOAD DATA`/`CREATE
  OR REPLACE TABLE ... FROM staging`** — só às consultas de transformação Silver/Gold e às
  consultas de leitura (API).
- **Achado adicional não previsto no DEFINE, relevante para o valor do cap:** "For clustered
  tables, the estimation of the number of bytes billed for a query is an upper bound, and can be
  higher than the actual number of bytes billed after running the query. So... a query on a
  clustered table can fail, even though the actual bytes billed wouldn't exceed the maximum bytes
  billed setting" (documentação oficial). **Toda tabela Silver/Gold do projeto usa `CLUSTER BY`**
  (convenção que este mesmo SPEC formaliza, G1) — ou seja, a estimativa pré-execução pode
  superestimar o custo real. Reforça a escolha de 1 GB (generoso) em vez de um valor mais
  agressivo: mesmo com a superestimativa do clustering, as tabelas do projeto (KB a poucos MB
  reais) estão muito longe do teto.
- **OQ2 (TTL de Bronze/Silver) — resolvida como decisão explícita de "não implementar TTL agora",
  não como silêncio:** Bronze/Silver são 100% recomputáveis a partir de RAW (todo pipeline já
  reprocessa do zero quando chamado de novo), mas o produto ainda não tem um caso de uso real que
  dependa de reconstruir Bronze/Silver histórico além do que já existe. Documentar a política como
  "sem TTL até haver pressão de custo real, revisar quando o armazenamento justificar" é honesto e
  correto — inventar um TTL sem necessidade seria adicionar risco (perda de dado) sem benefício
  medido.
- **OQ3 (queries administrativas) — resolvida.** `INFORMATION_SCHEMA.COLUMNS` e `SELECT
  COUNT(*)` são consultas de metadado/agregação trivial — mesmo a estimativa conservadora do
  BigQuery para essas não se aproxima de 1 GB nas tabelas do projeto (a maior tem ~15 mil linhas).
  Confirmado por raciocínio, não precisa de teste dedicado além dos testes de regressão já
  planejados (G6).

---

## 1. Grounding

| Padrão a reaproveitar | Fonte |
|---|---|
| `PARTITION BY reference_date` + `CLUSTER BY <chave de negócio>` | `sql/{silver,gold}/debt_state.sql`, `inss_beneficios_*.sql`, `fiscal_uniao.sql` — os 3 pares já existentes, extraídos literalmente para a seção de convenção do SPEC. |
| `ingestion/src/ingestion/bigquery_io.py::run_sql()` | Ponto único de toda chamada `client.query()` do lado de ingestão — o lugar certo para o cap por padrão. |
| `api/src/api/bigquery_repo.py::build_bigquery_run_query()` | Já constrói um `bigquery.QueryJobConfig` (para `query_parameters`) — só precisa ganhar mais um campo. |
| `ingestion/tests/_fakes.py::FakeBigQuery` | Fake compartilhado por praticamente todo teste de pipeline — 1 mudança aqui cobre todos os testes existentes automaticamente. |
| Precedente de SPEC transversal | `SPEC-031-CI-GATES.md` — molde de documento operacional não ligado a 1 domínio de produto. |

---

## 2. Arquitetura

```text
┌────────────────────────────────────────────────────────────────────┐
│  ingestion/src/ingestion/bigquery_io.py                             │
│                                                                      │
│  DEFAULT_MAX_BYTES_BILLED = 1_073_741_824  (1 GiB)                  │
│                                                                      │
│  def run_sql(client, sql, *,                                        │
│               maximum_bytes_billed=DEFAULT_MAX_BYTES_BILLED):       │
│      job_config = _job_config(maximum_bytes_billed)  # None = sem   │
│      return [dict(r) for r in client.query(sql, job_config).result()]│
└──────────────────────────┬───────────────────────────────────────────┘
                            │  default (cap ativo)              │ opt-out explícito
                            ▼                                    ▼
        ┌───────────────────────────────┐        ┌──────────────────────────────┐
        │ Silver/Gold SQL (todas as 3    │        │ bronze.py — LOAD DATA e       │
        │ fatias) via render_file()      │        │ CREATE OR REPLACE FROM        │
        │ registry.py / provenance.py    │        │ staging (D3: carga em lote,   │
        │ (D1 — protege contra mistake   │        │ billada como grátis, não como │
        │ de JOIN/filtro de partição)    │        │ bytes processados — cap       │
        │                                 │        │ desalinhado, arrisca quebrar  │
        │                                 │        │ arquivo-fonte grande real)    │
        └───────────────────────────────┘        └──────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│  api/src/api/bigquery_repo.py::build_bigquery_run_query()           │
│  job_config = bigquery.QueryJobConfig(                              │
│      query_parameters=job_params,                                   │
│      maximum_bytes_billed=DEFAULT_MAX_BYTES_BILLED,  # D2            │
│  )                                                                   │
└────────────────────────────────────────────────────────────────────┘
```

---

## 3. Decisões (ADRs inline)

### D1 — Cap de 1 GiB por padrão em `run_sql()`, aditivo via parâmetro opcional

| Atributo | Valor |
|---|---|
| Status | Accepted |
| Data | 2026-09-06 |

**Contexto:** `run_sql()` é o ponto único de toda chamada BigQuery do lado de ingestão
(pipeline de todas as 3 fatias, `registry.py`, `provenance.py`). Hoje não aplica nenhum
`job_config`.

**Escolha:** `run_sql(client, sql, *, maximum_bytes_billed: int | None =
DEFAULT_MAX_BYTES_BILLED)`. `DEFAULT_MAX_BYTES_BILLED = 1_073_741_824` (1 GiB). Quando `None`,
nenhum cap é aplicado (usado só pelas chamadas internas de `bronze.py`, D3). Nenhum caller
existente precisa mudar — o default já aplica o cap.

**Racional:** satisfaz C1 (aditivo) e S1 (100% das chamadas cobertas por padrão) ao mesmo tempo;
1 GiB é generoso o bastante para as tabelas reais do projeto (a maior, INSS Indeferidos, tem
~15 mil linhas — ordens de magnitude abaixo de 1 GB), mesmo considerando a superestimativa de
tabelas clusterizadas (`§0`).

**Alternativas rejeitadas:**
1. *Cap obrigatório (sem `None`)* — rejeitada: quebraria `bronze.py` (D3) ou exigiria uma função
   paralela sem cap, duplicando lógica.
2. *100 MB* — rejeitada por decisão do usuário no Brainstorm (mais restritivo do que o
   necessário para as tabelas reais do projeto).

**Consequências:** (+) proteção real contra erro grosseiro (JOIN sem filtro de partição) em
qualquer consulta de transformação; (+) zero mudança de comportamento para callers existentes.
(−) qualquer consulta futura legitimamente grande (ex.: uma fatia com volume real de GB) vai
precisar passar `maximum_bytes_billed` explicitamente maior — documentado no SPEC como o
procedimento esperado, não uma limitação escondida.

### D2 — Mesmo cap na API, direto no `QueryJobConfig` já existente

| Atributo | Valor |
|---|---|
| Status | Accepted |
| Data | 2026-09-06 |

**Contexto:** `build_bigquery_run_query()` já constrói um `bigquery.QueryJobConfig(
query_parameters=job_params)` para os parâmetros nomeados da query.

**Escolha:** o mesmo `QueryJobConfig` ganha `maximum_bytes_billed=DEFAULT_MAX_BYTES_BILLED`
(importado de `ingestion`? — **não**: API e `ingestion` são pacotes Python independentes, sem
dependência cruzada hoje; D2 define a constante localmente em `api/src/api/bigquery_repo.py`,
com o mesmo valor e o mesmo comentário explicativo, não uma importação entre pacotes).

**Racional:** menor mudança possível — o `job_config` já existe, só ganha mais um campo. Manter
os pacotes independentes (sem importar `ingestion` de dentro de `api/`) preserva a separação de
deploy que já existe (2 imagens Docker, 2 `pyproject.toml`).

**Alternativas rejeitadas:**
1. *Extrair uma constante compartilhada num pacote comum* — rejeitada: não existe hoje um
   pacote compartilhado entre `api/` e `ingestion/`; criar um só para uma constante é
   over-engineering para o escopo desta fatia.

**Consequências:** (+) API protegida com o mesmo padrão da ingestão; (−) o valor 1 GiB existe em
2 lugares (duplicação aceita, documentada nos comentários dos 2 arquivos apontando um pro outro).

### D3 — `bronze.py` opta explicitamente por não ter cap (LOAD DATA é carga, não consulta)

| Atributo | Valor |
|---|---|
| Status | Accepted |
| Data | 2026-09-06 |

**Contexto:** descoberta real (`§0`, OQ1): carga em lote (`LOAD DATA`) é billada como carga
(grátis), não como bytes processados — aplicar o cap aqui é um controle desalinhado, e um
arquivo-fonte real já foi visto na casa de 7+ GB (INSS Emitidos).

**Escolha:** as 2 chamadas internas de `bronze.load()`/`bronze.load_partition()` (`LOAD DATA
OVERWRITE`, `CREATE OR REPLACE TABLE ... FROM staging` / `INSERT INTO ... FROM staging`) passam
`maximum_bytes_billed=None` explicitamente.

**Racional:** o valor do cap é proteger contra *erro*, não bloquear *carga legítima*; uma carga
grande e esperada não é o cenário que este SPEC quer pegar.

**Alternativas rejeitadas:**
1. *Aplicar o cap em `bronze.py` também, com um valor maior (ex.: 50 GB)* — rejeitada: ainda é um
   número arbitrário sem embasamento real sobre o maior arquivo-fonte que o projeto algum dia vai
   processar; `None` é honesto sobre "esta função não tem esse tipo de proteção, por design".

**Consequências:** (+) nenhum risco de quebrar um backfill real de arquivo grande; (−) `bronze.py`
fica sem a mesma rede de segurança que o resto do pipeline — mitigado porque `LOAD DATA` é uma
operação estruturalmente diferente (carrega o arquivo inteiro por design, não "vaza" por engano
de JOIN).

### D4 — Convenção de particionamento/clustering formalizada, extraída do padrão real (não inventada)

| Atributo | Valor |
|---|---|
| Status | Accepted |
| Data | 2026-09-06 |

**Contexto:** os 3 pares Silver/Gold já existentes usam `PARTITION BY reference_date` +
`CLUSTER BY <chave(s) de negócio>` de forma 100% consistente, mas isso nunca foi escrito como
regra.

**Escolha:** `SPEC-034` documenta: toda tabela Silver/Gold nova DEVE particionar por um campo de
data de referência (`reference_date` ou equivalente truncado ao grão da tabela) e clusterizar
pela(s) chave(s) de negócio mais usada(s) em filtro/agrupamento (ex.: `state_ibge_code`,
`metric_id`, `especie_codigo`).

**Racional:** documenta o que já é verdade — nenhuma mudança de código necessária, só formaliza
a norma para a próxima fatia seguir sem precisar reinventar.

**Consequências:** (+) checklist objetivo pra revisão de PR futura; nenhuma contrapartida (não
muda código existente).

### D5 — Retenção: RAW permanente por princípio, Bronze/Silver/Gold sem TTL até pressão de custo real

| Atributo | Valor |
|---|---|
| Status | Accepted |
| Data | 2026-09-06 |

**Contexto:** `infra/terraform/storage.tf` já tem 1 `lifecycle_rule` parcial (limpa versões
`ARCHIVED` antigas do bucket RAW, não o dado RAW em si). Nenhuma política formal existe para
BigQuery em produção.

**Escolha:** `SPEC-034` declara explicitamente: (a) RAW é imutável e retido indefinidamente — é
o registro de auditoria da cadeia de proveniência (`SPEC-007`), nunca expirado automaticamente;
(b) Bronze/Silver são recomputáveis a partir de RAW a qualquer momento — sem TTL implementado
nesta fatia, revisar quando o volume de armazenamento justificar o custo de implementar; (c) Gold
e `metric_provenance` (dado público-facing) — sem TTL, são o produto em si.

**Racional:** resolve OQ2 como decisão documentada (G9, SHOULD), não como silêncio — sem
implementar automação que a fatia não tem evidência de precisar ainda (YAGNI).

**Consequências:** (+) política existe por escrito, decisão futura tem uma base para partir;
(−) nenhuma automação de fato reduz custo de armazenamento hoje — aceito, volume atual é
irrisório (KB a poucos MB por tabela).

---

## 4. Manifesto de arquivos

| # | Arquivo | Ação | Propósito | Agente | Deps |
|---|---|---|---|---|---|
| 1 | `docs/specs/SPEC-034-BIGQUERY-OPERATIONAL-STANDARDS.md` | Create | Formaliza D1-D5: cap de custo, particionamento/clustering, retenção | `architect` | — |
| 2 | `docs/adrs/ADR-057-bigquery-cost-guardrail.md` | Create | Formaliza D1-D3 (decisão de código do cap) | `architect` | — |
| 3 | `ingestion/src/ingestion/bigquery_io.py` | Modify | `DEFAULT_MAX_BYTES_BILLED`, `run_sql(..., maximum_bytes_billed=...)`, `BigQueryClient.query()` Protocol ganha `job_config` | `python-developer` | — |
| 4 | `ingestion/tests/_fakes.py` | Modify | `FakeBigQuery.query()` aceita e registra `job_config` (para os testes poderem inspecionar o cap aplicado) | `python-developer` | 3 |
| 5 | `ingestion/tests/test_bigquery_io.py` | Create | Testes novos: default aplica cap; `None` remove; `scalar()` idem | `python-reviewer` | 3,4 |
| 6 | `ingestion/src/ingestion/bronze.py` | Modify | `load()`/`load_partition()` passam `maximum_bytes_billed=None` (D3) | `python-developer` | 3 |
| 7 | `ingestion/tests/test_bronze_partition.py` | Modify | +asserção: chamadas de `bronze.py` não têm cap | `python-reviewer` | 4,6 |
| 8 | `api/src/api/bigquery_repo.py` | Modify | `build_bigquery_run_query()`: `QueryJobConfig` ganha `maximum_bytes_billed` (D2) | `python-developer` | — |
| 9 | `api/tests/test_bigquery_repo.py` | Modify | +teste (mock de `bigquery.Client`) confirmando o `job_config` real inclui o cap | `python-reviewer` | 8 |
| 10 | `docs/risks/RISK-CONTROL-TEST-MATRIX.md` | Modify | `R-012` distingue "cap por query: implementado" de "orçamento de projeto: não implementado" | `(general)` | 1,2 |
| 11 | `INDEX.md` | Modify | +SPEC-034, +ADR-057 | `(general)` | 1,2 |

### Racional de agentes
Documentos de norma/decisão → `architect`; mudança de código Python → `python-developer`;
revisão e testes → `python-reviewer`.

### Independência
Todos os itens de código (3,4,5,6,7,8,9) são independentes entre `ingestion/` e `api/` — podem
ser 1 PR só (sem dependência entre pacotes, ao contrário das fatias de dados que sempre
precisaram de PR1→PR2 sequencial). Os itens de documentação (1,2,10,11) não bloqueiam nem são
bloqueados pelo código — podem ir juntos no mesmo PR.

---

## 5. Padrões de código

### 5.1 `bigquery_io.py` — cap por padrão, opt-out explícito

```python
from google.cloud import bigquery  # já usado em build_bigquery_run_query equivalente

DEFAULT_MAX_BYTES_BILLED = 1_073_741_824  # 1 GiB — ver ADR-057


class BigQueryClient(Protocol):
    def query(
        self, query: str, job_config: bigquery.QueryJobConfig | None = None
    ) -> QueryJob: ...


def run_sql(
    client: BigQueryClient,
    sql: str,
    *,
    maximum_bytes_billed: int | None = DEFAULT_MAX_BYTES_BILLED,
) -> list[dict[str, Any]]:
    job_config = None
    if maximum_bytes_billed is not None:
        job_config = bigquery.QueryJobConfig(maximum_bytes_billed=maximum_bytes_billed)
    return [dict(row) for row in client.query(sql, job_config).result()]
```

### 5.2 `bronze.py` — opt-out explícito (D3)

```python
run_sql(client, f"LOAD DATA OVERWRITE {staging} (...) FROM FILES (...)", maximum_bytes_billed=None)
run_sql(client, f"CREATE OR REPLACE TABLE {target} AS SELECT ... FROM {staging}", maximum_bytes_billed=None)
```

### 5.3 `bigquery_repo.py` — mesmo cap no `job_config` já existente

```python
DEFAULT_MAX_BYTES_BILLED = 1_073_741_824  # 1 GiB — mesmo valor de ingestion/bigquery_io.py (ADR-057)

job_config = bigquery.QueryJobConfig(
    query_parameters=job_params,
    maximum_bytes_billed=DEFAULT_MAX_BYTES_BILLED,
)
```

### 5.4 `_fakes.py` — Fake registra o `job_config` recebido

```python
class FakeBigQuery:
    def __init__(self, responder=None) -> None:
        self.queries: list[str] = []
        self.job_configs: list[Any] = []
        self._responder = responder or (lambda _sql: [])

    def query(self, query: str, job_config: Any = None) -> _FakeQueryJob:
        self.queries.append(query)
        self.job_configs.append(job_config)
        return _FakeQueryJob(self._responder(query))
```

---

## 6. Estratégia de testes

| Tipo | Escopo | Ferramenta |
|---|---|---|
| Unit — `bigquery_io.py` | Default aplica `maximum_bytes_billed=1_073_741_824`; `None` explícito não aplica cap algum; `scalar()` herda o mesmo comportamento | `pytest` |
| Unit — `bronze.py` | `load()`/`load_partition()` sempre chamam `run_sql` com `maximum_bytes_billed=None` (regressão contra opt-out acidentalmente removido) | `pytest` |
| Unit — `bigquery_repo.py` | `build_bigquery_run_query()` real (mock de `bigquery.Client`/`QueryJobConfig`) confirma o cap no `job_config` construído | `pytest` + `unittest.mock` |
| Regressão — as 3 fatias | `ingestion/`/`api/` suites completas continuam verdes com o cap ativo por padrão (nenhuma query real do projeto se aproxima de 1 GiB) | `pytest` |
| Integração | Gate `integration` do `ci.yml` (já roda os 3 pipelines contra BigQuery real) — nenhuma mudança de infraestrutura, só confirma que o cap não quebra nada real | `pytest -m integration` (CI) |

Cobre todos os acceptance tests do DEFINE (AT1–AT8; AT4 usa um cap artificialmente baixo no
próprio teste, não uma tabela real de 1 GB, para provar a falha sem custo real).

---

## 7. Pipeline Architecture (contexto DE)

Não aplicável no sentido usual (esta fatia não introduz um pipeline de dado novo) — mas afeta
**todos** os pipelines existentes de forma transversal:

| Aspecto | Definição |
|---|---|
| **Escopo do controle** | Toda consulta de transformação (Silver/Gold, `registry`, `provenance`) e toda leitura da API — não a carga (`LOAD DATA`), por design (D3). |
| **Falha esperada** | `google.api_core.exceptions.BadRequest` (ou subclasse equivalente) quando uma query estimada excede o cap — tratada como erro visível, não silenciado, propagada normalmente pelas exceções já existentes de cada pipeline. |
| **Sem mudança de schema/dado** | Este SPEC não altera nenhuma tabela Bronze/Silver/Gold existente — é puramente uma mudança de como as queries são *emitidas*, não do que elas retornam. |

---

## 8. Quality gate (Fase 2)

- [x] Descoberta real feita — comportamento de billing pesquisado via documentação oficial, não suposto (`§0`)
- [x] ASCII diagram criado e claro (`§2`)
- [x] Pelo menos 1 decisão com racional completo (5 decisões, D1-D5)
- [x] Manifesto de arquivos completo (11 itens)
- [x] Agente atribuído a cada arquivo
- [x] Padrões de código sintaticamente corretos, prontos para copiar-adaptar
- [x] Estratégia de testes cobre todos os acceptance tests do DEFINE (AT1-AT8)
- [x] Sem dependência circular na arquitetura
- [x] Achado técnico (D3 — LOAD DATA é carga grátis, cap desalinhado) documentado ANTES do build
- [x] DEFINE status → `✅ Complete (Designed)`

---

## 9. Handoff

Pronto para `/build .claude/sdd/features/DESIGN_BIGQUERY_OPERATIONAL_STANDARDS.md`.

---

## 10. Revision history

| Data | Versão | Mudança | Autor |
|---|---|---|---|
| 2026-09-06 | 1.0 | Criação a partir de `DEFINE_BIGQUERY_OPERATIONAL_STANDARDS.md`. Descoberta real (§0) resolveu OQ1-OQ3 via pesquisa na documentação oficial do BigQuery (batch loading é grátis; estimativa de tabela clusterizada é upper bound). 5 decisões inline (D1-D5), incluindo D3 (bronze.py opta por não ter cap — achado que evita quebrar cargas de arquivo grande real, já visto no INSS). Manifesto 11 itens. Status → Ready for Build. | /design (Claude Sonnet 5) |
| 2026-09-06 | 1.1 | Build completo; `/verify-spec` independente = OVERALL PASS. Shipped and archived. | /ship (Claude Sonnet 5) |
