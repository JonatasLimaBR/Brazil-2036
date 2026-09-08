# DESIGN — DEBTLAB_SIMULATOR

## Metadados

- **Feature:** DEBTLAB_SIMULATOR
- **Status:** ✅ Shipped

> Shipped and archived 2026-09-08.
- **Fase:** 2 (Design)
- **Entrada:** `.claude/sdd/features/DEFINE_DEBTLAB_SIMULATOR.md` (Clarity 13/15)
- **Criado:** 2026-09-07
- **Idioma:** PT-BR
- **Branch:** a criar — `feature/debtlab-simulator`
- **Confiança:** 0.8 — descoberta real confirmou fonte de dado (API pública do BCB, sem
  autenticação) e resolveu um desalinhamento conceitual real (`§0.2`); incerteza residual normal
  de "primeiro simulador do projeto" (nenhum precedente de engine determinístico no repo).
- **Próximo passo:** `/build .claude/sdd/features/DESIGN_DEBTLAB_SIMULATOR.md`

> Nota: assets do plugin SDD ausentes — documento segue a lista de seções do skill `sdd-design`.

---

## 0. Descoberta real (resolve OQ1–OQ6 do DEFINE)

### 0.1 Fonte de PIB e dívida — API real do BCB, inspecionada de verdade (OQ1)

`docs/sources/SOURCE-INDEX.csv` já lista **Banco Central (BCB)** como fonte **P0** para o domínio
"Macro/monetário" — não é uma fonte nova para o projeto, só nunca usada ainda. A API SGS do BCB
(`https://api.bcb.gov.br/dados/serie/bcdata.sgs.{código}/dados?formato=json`) é pública, sem
autenticação, confirmada real nesta sessão via chamada direta:

- **Série 4380 — PIB mensal, valores correntes (R$ milhões).** Confirmado real: últimos 5 pontos
  retornados vão de 03/2026 a 07/2026, valores entre R$ 1.128.771,2 e R$ 1.176.973,0 milhões/mês —
  ordem de grandeza consistente com um PIB mensal nominal do Brasil em 2026 (~R$ 14 tri/ano
  projetado, plausível partindo de ~R$ 11,4 tri em 2024 do IBGE).
- **Série 13762 — Dívida Bruta do Governo Geral (% PIB), metodologia 2008+.** Confirmado real:
  últimos 5 pontos vão de 79,88% (03/2026) a 82,51% (07/2026) — consistente com a trajetória
  pública conhecida da dívida bruta brasileira.

Ambas atualizadas mensalmente, sem necessidade de scraping/CKAN — só `GET` HTTP simples.

### 0.2 Achado real que muda o desenho: `divida_consolidada` não é a métrica certa para o DebtLab

`SIM-002`/`SPEC-010` pedem "base debt/GDP" — no vocabulário de sustentabilidade fiscal, isso é a
**dívida bruta do governo geral, nacional**. O `divida_consolidada` que o projeto já tem
(`MVP_WALKING_SKELETON`) é outra coisa: dívida das 27 UFs sob o **PAF** (Programa de
Reestruturação e Ajuste Fiscal), só 2022, sem série temporal. São conceitos diferentes — usar
`divida_consolidada` como base do simulador seria uma métrica errada, não uma simplificação
aceitável. **Decisão:** o DebtLab usa a série 13762 (Dívida Bruta do Governo Geral, % PIB) como
base real, nacional, mensal — resolve `OQ2` do DEFINE ("somar as 27 UFs?" fica sem sentido, a
pergunta não se aplica mais). `divida_consolidada` continua existindo e servida como está, sem
nenhuma mudança; esta fatia não a toca.

### 0.3 Fórmula: reformulação para a equação padrão de dinâmica da dívida (razão, não R$ absoluto)

O rascunho do `/define` («dívida_t = dívida_(t-1)×(1+juros) − primário_t, dividido pelo PIB»)
exigiria projetar PIB em R$ para todo o horizonte. A **equação padrão de sustentabilidade fiscal**
(literatura de finanças públicas, e o que `SPEC-010` já sugere com "real/nominal rates as selected
methodology") evita isso ao trabalhar direto com razões:

```text
razão_t = razão_(t-1) × (1 + juros_nominal) / (1 + crescimento_nominal_PIB) − primário_%PIB_t
```

- `razão_0` = último valor real da série 13762 (ex.: 82,51% em 07/2026).
- `juros_nominal`, `crescimento_nominal_PIB`, `primário_%PIB` = premissas do cenário (entrada do
  usuário, com média±desvio para o Monte Carlo).
- Nenhuma projeção de PIB em R$ é necessária — mais simples, mais robusto, e o padrão que a
  literatura de dívida pública usa de fato. `crescimento` volta a ser uma premissa central (o
  usuário pediu explicitamente para não simplificar).

### 0.4 Achado real de infraestrutura: API hoje é 100% somente-leitura, sem esta fatia muda isso

`infra/terraform/cloud_run_services.tf`: a service account `api-runtime` tem `display_name =
"Metrics API runtime (read-only on Gold)"` e só `roles/bigquery.dataViewer` no dataset **gold** —
nenhuma permissão de escrita, nenhum acesso ao dataset **control**. Esta é a primeira fatia em que
a API precisa **gravar** (persistir cenário/resultado). Mudança de Terraform real e necessária:
`google_bigquery_dataset_iam_member` novo, `roles/bigquery.dataEditor` escopado só ao dataset
`br2036_control` (não projeto inteiro) — mesmo princípio de least-privilege já usado para o
`ingestion_job`. `display_name` do service account atualizado para não ficar desatualizado.

Também: `main.py` hoje só permite `allow_methods=["GET"]` no CORS (`ADR-044`, API pública
read-only). O endpoint novo é `POST` — CORS precisa incluir `POST` explicitamente. Continua público
sem autenticação (mesmo padrão de hoje — RBAC/ABAC é a próxima fatia da sequência combinada, fora
de escopo aqui, `C6` do DEFINE).

### 0.5 `br2036_control` já existe e já é o lugar certo (confirma decisão do usuário)

`infra/terraform/bigquery.tf`: o dataset `control` já está descrito literalmente como *"Registry,
reference tables and run bookkeeping"* — encaixe semântico direto para armazenar cenários de
simulação, sem precisar criar dataset novo nem justificar uma exceção.

### 0.6 Achado real de risco operacional: escrita pública sem RBAC ainda

Sem RBAC (fora de escopo desta fatia), `POST /v1/simulations/debtlab` fica público, como todo o
resto da API hoje. Diferença real: é a primeira rota que **grava**. BigQuery tem cotas de DML por
tabela (variam por edição/projeto) — um abuso trivial (loop de requests) poderia esgotar a cota do
dia. **Mitigação proporcional ao MVP** (não constrói rate-limiting novo, que seria escopo da
próxima fatia de RBAC): validação de input com limites defensivos (`n_iterations` entre 100 e
20.000, `horizon_years` entre 1 e 30) — barato de implementar, reduz o pior caso de custo por
request sem precisar de infraestrutura nova. Risco residual documentado em `§9` do BUILD_REPORT
como aceito para o V1, revisitado quando RBAC/rate-limiting existir.

---

## 1. Grounding

| Padrão a reaproveitar | Fonte |
|---|---|
| `Connector` Protocol (`discover`/`metadata`/`download`/`validate`/`checkpoint`) | `ingestion/src/ingestion/connectors/base.py` — reaproveitado como está, novo conector implementa o Protocol. |
| Pipeline RAW→Bronze→Silver→Gold genérico | `ingestion/src/ingestion/{bronze,contract,provenance,registry,pipeline_incremental}.py` — já generalizados de forma aditiva (achado do `BIGQUERY_OPERATIONAL_STANDARDS`); esta fatia não deveria precisar tocar esses arquivos. |
| `config.metric_tables: metric_id -> gold_table` + rota `/v1/metrics/{metric_id}/national` | `api/src/api/{config,main,bigquery_repo}.py` — os 2 metric_ids novos (`pib_mensal`, `divida_bruta_pib`) são servidos **sem nenhum código novo**, só entradas de config, mesmo padrão do INSS/Fiscal. |
| `RunQuery` (query parametrizada) | `api/src/api/bigquery_repo.py::build_bigquery_run_query()` — reaproveitado para o INSERT do cenário via DML parametrizado, sem precisar de um client BigQuery novo. |
| `DataClass.simulated` | `api/src/api/models.py` — já existe no enum (`"simulated"`), não precisa ser criado. |
| Cap de bytes (`ADR-057`) | Aplicado nas novas queries de leitura; a query de INSERT usa `maximum_bytes_billed=None` explícito (DML de 1 linha, não é um SELECT a ser limitado por bytes escaneados — mesmo racional de `bronze.py` para `LOAD DATA`, `DESIGN D2`). |
| Conferência manual contra fonte oficial | Mesmo padrão de `FISCAL_RECEITA_DESPESA` (jul/2026 bateu exatamente) — aqui, conferir a razão dívida/PIB do último mês real contra a série 13762 diretamente. |

---

## 2. Arquitetura

```text
┌──────────────────────────────────────────────────────────────────────────┐
│  ingestion/ (RAW → Bronze → Silver → Gold, reaproveita infra existente)  │
│                                                                            │
│  BcbSgsConnector(series_code=4380, metric_id="pib_mensal")                │
│  BcbSgsConnector(series_code=13762, metric_id="divida_bruta_pib")         │
│    └─ GET https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados      │
│       → RAW (JSON bruto) → Bronze (CSV long) → Silver → Gold              │
│       (mesmo pipeline_incremental.py já usado no INSS)                    │
│                                                                            │
│  gold_bcb_macro  (1 tabela, 2 metric_id, reference_date, value, unit)     │
└──────────────────────────┬─────────────────────────────────────────────────┘
                             │ metric_tables: pib_mensal, divida_bruta_pib
                             ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  api/src/api/ (FastAPI, Cloud Run)                                       │
│                                                                            │
│  GET  /v1/metrics/pib_mensal/national            ── já genérico, 0 código│
│  GET  /v1/metrics/divida_bruta_pib/national       ── já genérico, 0 código│
│                                                                            │
│  api/src/api/simulators/debtlab.py    ── engine determinístico (puro)    │
│  api/src/api/simulators/monte_carlo.py ── amostragem normal + percentis  │
│                                                                            │
│  POST /v1/simulations/debtlab   ── lê base real (13762), roda engine,    │
│                                     grava cenário em br2036_control        │
│  GET  /v1/simulations/debtlab/{scenario_id}  ── lê cenário persistido     │
└──────────────────────────┬─────────────────────────────────────────────────┘
                             │
                             ▼
                 br2036_control.debtlab_scenarios
                 (scenario_id, assumptions, base, trajetória, percentis,
                  engine_version, seed, data_class=SIMULATED)
```

---

## 3. Decisões (ADRs inline)

### D1 — BCB SGS como fonte de PIB e dívida bruta, `divida_consolidada` não é reaproveitado

| Atributo | Valor |
|---|---|
| Status | Accepted |
| Data | 2026-09-07 |

**Contexto:** `SIM-002` pede "base debt/GDP" nacional; o projeto não tem PIB real, e a única dívida
real hoje (`divida_consolidada`) é um conceito diferente (PAF, por UF, só 2022) — `§0.2`.

**Escolha:** BCB SGS (série 4380 PIB, série 13762 Dívida Bruta do Governo Geral % PIB), fonte já
listada como P0 no `SOURCE-INDEX.csv`, confirmada real por chamada direta à API pública.

**Racional:** dado nacional, mensal, atualizado, exatamente o conceito que `SPEC-010` pede — sem
precisar reconciliar/agregar `divida_consolidada` (que resolveria a pergunta errada).

**Alternativas rejeitadas:** IBGE Contas Nacionais/SIDRA (série trimestral, mais granular pra PIB
real mas sem uma série de dívida/PIB equivalente pronta — exigiria combinar 2 fontes diferentes,
mais complexo sem ganho claro para o V1); reaproveitar `divida_consolidada` como base (métrica
errada, rejeitado no `§0.2`).

**Consequências:** (+) fonte única para as 2 séries, já confirmada real; (+) mensal, mais atual que
trimestral. (−) metodologia do BCB (2008+) limita a série histórica a partir de 2008, suficiente
para o V1 (não precisamos de histórico anterior a isso).

### D2 — Fórmula: razão dívida/PIB, não reconstrução em R$ absoluto

| Atributo | Valor |
|---|---|
| Status | Accepted |
| Data | 2026-09-07 |

**Contexto:** o rascunho do `/define` exigiria projetar PIB em R$ para todo o horizonte, mais
código e mais superfície de erro.

**Escolha:** equação padrão `razão_t = razão_(t-1) × (1+juros)/(1+crescimento) − primário_%PIB_t`
(`§0.3`), sem projetar PIB em R$.

**Racional:** é o padrão da literatura de sustentabilidade fiscal, mais simples de implementar e
testar, e ainda usa a dívida/PIB **real** como base — não é uma simplificação que perde dado real,
é a forma correta de modelar a dinâmica.

**Consequências:** (+) menos código, menos estado a propagar; (+) `primário` como %PIB é mais
natural pra premissa de cenário do que R$ absoluto. (−) usuário informa premissas em %PIB, não em
R$ — precisa de uma nota clara na API/doc sobre a unidade esperada.

### D3 — Engine e Monte Carlo vivem em `api/`, não em `ingestion/`

| Atributo | Valor |
|---|---|
| Status | Accepted |
| Data | 2026-09-07 |

**Contexto:** `ingestion/` é hoje só pipelines batch RAW→Gold; o engine do DebtLab é computação
síncrona disparada por requisição HTTP, sem GCS/RAW envolvido.

**Escolha:** `api/src/api/simulators/{debtlab,monte_carlo}.py` — novo subpacote dentro de `api/`.

**Racional:** o engine só precisa ler o dado real já em Gold (via `BigQueryRepo`, já existe) e
gravar o resultado — nenhuma dependência do pipeline de ingestão. Colocar em `ingestion/`
misturaria dois tipos de responsabilidade (pipeline batch vs. compute síncrono de API).

**Alternativas rejeitadas:** `ingestion/src/ingestion/simulators/` (rascunho do `/define`) —
rejeitado porque o engine não é chamado pelo pipeline de ingestão em nenhum momento, só pela API.

**Consequências:** (+) separação de responsabilidade clara; (+) futuros simuladores seguem o mesmo
lugar. (−) nenhuma — não há acoplamento perdido, o engine já não dependia de nada de `ingestion/`.

### D4 — Persistência de cenário em `br2036_control` (BigQuery), não AlloyDB

| Atributo | Valor |
|---|---|
| Status | Accepted |
| Data | 2026-09-07 |

**Contexto:** `ADR-004` decidiu AlloyDB para estado operacional, mas nunca foi provisionado
(`§0.4`); sem approval workflow/checkpoint real ainda que justifique o custo fixo, contra o driver
de custo do `ADR-002` (serverless-first). Decisão já confirmada com o usuário no `/brainstorm`.

**Escolha:** tabela `br2036_control.debtlab_scenarios` — dataset já existe, já descrito como
"Registry, reference tables and run bookkeeping" (`§0.5`), zero infra nova.

**Racional:** BigQuery já provisionado, já usado para 2 tabelas operacionais análogas
(`dataset_registry`, `metric_provenance`) — cenário de simulação é o mesmo tipo de "bookkeeping".

**Consequências:** (+) zero custo/infra nova; (+) consistente com o que `br2036_control` já
guarda. (−) BigQuery não é feito para muitas escritas pequenas/transacionais (cotas de DML,
`§0.6`) — aceitável no volume esperado do V1; `ADR-004` continua válido para quando
approval/checkpoint de agente virarem reais (nota, não superseded).

### D5 — Estrutura de linha do resultado: campos estruturados JSON-como-STRING, não `ARRAY<STRUCT>`

| Atributo | Valor |
|---|---|
| Status | Accepted |
| Data | 2026-09-07 |

**Contexto:** `RunQuery` (padrão já existente em `bigquery_repo.py`) só infere `INT64`/`STRING`
para parâmetros de query; `ARRAY<STRUCT>` como parâmetro de DML exigiria estender bastante essa
abstração.

**Escolha:** `trajetoria_deterministica` e `percentis` são colunas `STRING` com JSON serializado
(`json.dumps`); a API deserializa na leitura. `RunQuery`/`build_bigquery_run_query()` ganha
inferência de tipo pra `float` (`FLOAT64`), aditivo.

**Racional:** menos código novo, evita expandir a abstração de query parametrizada para tipos
complexos por causa de 1 tabela; BigQuery consegue named-JSON via `STRING` sem problema para o
consumo que existe hoje (só a própria API lê essa tabela).

**Consequências:** (+) `RunQuery` continua simples; (+) menos superfície de mudança em código já
testado. (−) se no futuro alguém quiser consultar `debtlab_scenarios` direto via SQL analítico
(não só pela API), vai precisar de `JSON_EXTRACT`/`PARSE_JSON` em vez de `UNNEST` nativo — aceitável
pro V1, tabela é consumida só pela própria API.

---

## 4. Manifesto de arquivos

| # | Arquivo | Ação | Propósito | Agente | Deps |
|---|---|---|---|---|---|
| 1 | `ingestion/src/ingestion/connectors/bcb_sgs.py` | Create | `BcbSgsConnector` genérico (Protocol de `base.py`), parametrizado por `series_code`/`metric_id`, implementa fetch JSON real do BCB (D1) | `python-developer` | — |
| 2 | `ingestion/contracts/pib_mensal.yaml` | Create | Contrato do metric_id `pib_mensal` (unidade R$ milhões, `data_class=observed`) | `data-contracts-engineer` | — |
| 3 | `ingestion/contracts/divida_bruta_pib.yaml` | Create | Contrato do metric_id `divida_bruta_pib` (unidade % PIB, `data_class=observed`, `allow_negative=false`) | `data-contracts-engineer` | — |
| 4 | `ingestion/sql/silver/bcb_macro.sql` | Create | Silver do par PIB/dívida-PIB, mesmo padrão `PARTITION BY reference_date CLUSTER BY metric_id` (`SPEC-034`) | `gcp-data-architect` | 1 |
| 5 | `ingestion/sql/gold/gold_bcb_macro.sql` | Create | Gold consolidado, 1 tabela 2 metric_id (mesmo padrão de `gold_fiscal_uniao`) | `gcp-data-architect` | 4 |
| 6 | `ingestion/scripts/run_bcb_macro.py` (ou equivalente CLI) | Create | Entry point de backfill/execução incremental, reaproveita `pipeline_incremental.py` | `python-developer` | 1, 4, 5 |
| 7 | `api/src/api/simulators/__init__.py` | Create | Marca o subpacote novo | `(general)` | — |
| 8 | `api/src/api/simulators/debtlab.py` | Create | Engine determinístico puro (D2/D3): `project_deterministic(base_ratio, horizon_years, assumptions) -> list[YearPoint]` | `python-developer` | 7 |
| 9 | `api/src/api/simulators/monte_carlo.py` | Create | Amostragem normal (numpy), N iterações, P10/P25/P50/P75/P90, seed fixável (`SPEC-016`) | `python-developer` | 8 |
| 10 | `api/src/api/models.py` | Modify | + `ScenarioRequest`, `ScenarioResponse`, `YearlyDeterministic`, `YearlyPercentiles` (aditivo, `DataClass.simulated` já existe) | `typescript-reviewer` → não, `python-developer` | — |
| 11 | `api/src/api/bigquery_repo.py` | Modify | + `create_scenario()`/`get_scenario()` (INSERT/SELECT parametrizado em `br2036_control.debtlab_scenarios`); `build_bigquery_run_query()` ganha inferência `float→FLOAT64` (D5) | `python-developer` | 9, 10 |
| 12 | `api/src/api/main.py` | Modify | + `POST /v1/simulations/debtlab`, `GET /v1/simulations/debtlab/{scenario_id}`; CORS `allow_methods` ganha `"POST"` (`§0.4`); validação defensiva de `n_iterations`/`horizon_years` (`§0.6`) | `python-developer` | 11 |
| 13 | `api/src/api/config.py` / `config.yaml` | Modify | + `metric_tables: pib_mensal, divida_bruta_pib`; + nome da tabela de cenários (`br2036_control.debtlab_scenarios`) | `(general)` | — |
| 14 | `infra/terraform/cloud_run_services.tf` | Modify | + `google_bigquery_dataset_iam_member` (`dataEditor` em `br2036_control` para `api-runtime`); atualiza `display_name` (`§0.4`) | `ci-cd-specialist` | — |
| 15 | `docs/adrs/ADR-059-debtlab-engine-and-persistence.md` | Create | Formaliza D1–D5 | `architect` | 1–14 |
| 16 | `ingestion/tests/connectors/test_bcb_sgs.py` | Create | Testes do conector (fetch, parse, checkpoint) | `test-generator` | 1 |
| 17 | `api/tests/test_debtlab_engine.py` | Create | Testes unitários da fórmula (`AT1`), casos sintéticos calculados à mão | `test-generator` | 8 |
| 18 | `api/tests/test_monte_carlo.py` | Create | Testes de reprodutibilidade com `seed` fixo (`AT3`) | `test-generator` | 9 |
| 19 | `api/tests/test_simulations_endpoint.py` | Create | Testes de contrato do endpoint (`AT2`, `AT5`, `AT6`) | `test-generator` | 12 |
| 20 | `docs/risks/RISK-CONTROL-TEST-MATRIX.md` | Modify | Registra risco de escrita pública sem rate-limit (`§0.6`) como aceito para o V1 | `(general)` | — |

### Racional de agentes
Conector/engine/testes Python → `python-developer`/`test-generator` (mesmo padrão já usado);
contrato/SQL → `data-contracts-engineer`/`gcp-data-architect`; Terraform → `ci-cd-specialist`; ADR →
`architect`; config/risco → `(general)`.

### Independência
Ingestão (itens 1–6) e engine/API (itens 7–13) são paralelizáveis entre si — o engine só depende
da leitura via `BigQueryRepo` existente, que já sabe ler qualquer `metric_id`/`gold_table`
configurado. O endpoint `POST` (item 12) depende de ambos estarem prontos (precisa da dívida/PIB
real em Gold para ler a base do cenário). Terraform (14) é independente, pode ir num PR próprio se
o `/build` preferir (mesmo padrão de PRs separados já usado nesta sessão).

---

## 5. Padrões de código

### 5.1 `BcbSgsConnector` — genérico, parametrizado por série

```python
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from ingestion.connectors.base import ConnectorError, DownloadResult, ResourceRef

_BASE_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"


@dataclass(frozen=True)
class BcbSgsSeries:
    series_code: int
    metric_id: str
    unit: str


class BcbSgsConnector:
    """Fetches one BCB SGS time series (public JSON API, no auth).

    One instance per series -- pib_mensal (4380) and divida_bruta_pib (13762)
    are two separate instances of the same connector, not two classes
    (DESIGN D1: identical API shape, only the series code/metric_id differ).
    """

    dataset_id = "bcb_sgs"

    def __init__(self, *, session: object, series: BcbSgsSeries, request_timeout: float = 30.0) -> None:
        self._session = session
        self._series = series
        self._request_timeout = request_timeout

    def discover(self) -> ResourceRef:
        url = _BASE_URL.format(code=self._series.series_code) + "?formato=json"
        return ResourceRef(
            dataset_id=self.dataset_id, resource_url=url, resource_format="json", resource_hash=None
        )

    def metadata(self, ref: ResourceRef) -> dict[str, str]:
        return {"series_code": str(self._series.series_code), "metric_id": self._series.metric_id}

    def download(self, ref: ResourceRef, dest: str) -> DownloadResult:
        response = self._session.get(ref.resource_url, timeout=self._request_timeout)
        response.raise_for_status()
        data = response.content
        with open(dest, "wb") as handle:
            handle.write(data)
        return DownloadResult(
            local_path=dest,
            content_sha256=hashlib.sha256(data).hexdigest(),
            http_status=response.status_code,
            bytes_downloaded=len(data),
            attempts=1,
            attempt_errors=[],
        )

    def validate(self, local_path: str) -> None:
        with open(local_path, "rb") as handle:
            rows = json.loads(handle.read())
        if not isinstance(rows, list) or not rows:
            raise ConnectorError(f"BCB SGS {self._series.series_code}: empty or malformed payload")
        for row in rows[:1]:
            if "data" not in row or "valor" not in row:
                raise ConnectorError(f"BCB SGS {self._series.series_code}: unexpected row shape {row!r}")

    def checkpoint(self, ref: ResourceRef, content_sha256: str) -> bool:
        return ref.resource_hash != content_sha256
```

### 5.2 Engine determinístico (`api/src/api/simulators/debtlab.py`)

```python
from __future__ import annotations

from dataclasses import dataclass

ENGINE_VERSION = "debtlab-v1"


@dataclass(frozen=True)
class Assumptions:
    juros_nominal: float
    crescimento_nominal_pib: float
    primario_pct_pib: float


@dataclass(frozen=True)
class YearPoint:
    year_offset: int
    divida_pib_pct: float


def project_deterministic(
    base_ratio_pct: float, horizon_years: int, assumptions: Assumptions
) -> list[YearPoint]:
    """SPEC-010: dívida/PIB dynamics, no LLM path may replace this."""
    ratio = base_ratio_pct / 100
    points = [YearPoint(year_offset=0, divida_pib_pct=base_ratio_pct)]
    for year in range(1, horizon_years + 1):
        ratio = (
            ratio * (1 + assumptions.juros_nominal) / (1 + assumptions.crescimento_nominal_pib)
            - assumptions.primario_pct_pib
        )
        points.append(YearPoint(year_offset=year, divida_pib_pct=ratio * 100))
    return points
```

### 5.3 Monte Carlo (`api/src/api/simulators/monte_carlo.py`)

```python
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from api.simulators.debtlab import project_deterministic, Assumptions


@dataclass(frozen=True)
class AssumptionDistribution:
    mean: float
    std: float


@dataclass(frozen=True)
class YearPercentiles:
    year_offset: int
    p10: float
    p25: float
    p50: float
    p75: float
    p90: float


def run_monte_carlo(
    base_ratio_pct: float,
    horizon_years: int,
    juros: AssumptionDistribution,
    crescimento: AssumptionDistribution,
    primario: AssumptionDistribution,
    n_iterations: int,
    seed: int,
) -> list[YearPercentiles]:
    """SPEC-016: explicit distributions, seed fixable for reproducibility."""
    rng = np.random.default_rng(seed)
    juros_samples = rng.normal(juros.mean, juros.std, n_iterations)
    crescimento_samples = rng.normal(crescimento.mean, crescimento.std, n_iterations)
    primario_samples = rng.normal(primario.mean, primario.std, n_iterations)

    trajectories = np.empty((n_iterations, horizon_years + 1))
    for i in range(n_iterations):
        points = project_deterministic(
            base_ratio_pct,
            horizon_years,
            Assumptions(juros_samples[i], crescimento_samples[i], primario_samples[i]),
        )
        trajectories[i] = [p.divida_pib_pct for p in points]

    percentiles = np.percentile(trajectories, [10, 25, 50, 75, 90], axis=0)
    return [
        YearPercentiles(year_offset=y, p10=percentiles[0][y], p25=percentiles[1][y],
                         p50=percentiles[2][y], p75=percentiles[3][y], p90=percentiles[4][y])
        for y in range(horizon_years + 1)
    ]
```

---

## 6. Estratégia de testes

| Tipo | Escopo | Ferramenta |
|---|---|---|
| Unit — engine | Fórmula de dinâmica contra casos sintéticos calculados à mão (`AT1`) | `pytest` |
| Unit — Monte Carlo | Reprodutibilidade com `seed` fixo; distribuição de saída plausível (`AT3`) | `pytest` |
| Unit — conector BCB SGS | Fetch/parse/checkpoint com resposta HTTP fake | `pytest` |
| Contract — endpoints | `POST` cria e persiste; `GET` retorna o mesmo resultado (`AT2`); `data_class=simulated` sempre presente (`AT5`) | `pytest` + `TestClient` do FastAPI |
| Manual — conferência de ground truth | Razão dívida/PIB do mês mais recente batendo contra a série 13762 (`AT4`), mesmo padrão do Fiscal | Execução real contra `brasil2036-dev` |
| Integration (CI) | `pytest -m integration` contra BigQuery real, incluindo o INSERT/SELECT de cenário | `ci / integration` (`SPEC-031`) |

Cobre AT1–AT8 do DEFINE.

---

## 7. Pipeline Architecture (contexto DE)

| Aspecto | Definição |
|---|---|
| **Fonte** | API JSON pública do BCB SGS, sem autenticação (`§0.1`). |
| **Estratégia de carga** | Incremental — mesmo padrão do INSS (`pipeline_incremental.py`), busca só os períodos novos desde o último checkpoint. |
| **Particionamento/clustering** | `PARTITION BY reference_date CLUSTER BY metric_id` (`SPEC-034`, mesmo padrão já usado). |
| **Qualidade de dado** | Contrato por `metric_id` (`pib_mensal`, `divida_bruta_pib`) verificando unidade, ausência de nulo, `allow_negative=false` para a razão dívida/PIB. |
| **Evolução de schema** | Mesmo padrão aditivo já usado — nenhuma mudança esperada na API do BCB SGS (série estável há anos). |

---

## 8. Quality gate (Fase 2)

- [x] Descoberta real feita — fonte confirmada por chamada real à API, achado conceitual real
  (`divida_consolidada` ≠ base do simulador) corrigido antes do código, achado de infra real
  (API read-only, CORS, dataset `control`) confirmado por leitura do Terraform/código atual
- [x] ASCII diagram criado e claro (`§2`)
- [x] Pelo menos 1 decisão com racional completo (5 decisões, D1–D5)
- [x] Manifesto de arquivos completo (20 itens)
- [x] Agente atribuído a cada arquivo
- [x] Padrões de código sintaticamente corretos, prontos para copiar-adaptar
- [x] Estratégia de testes cobre os acceptance tests do DEFINE (AT1–AT8)
- [x] Sem dependência circular na arquitetura
- [x] Nenhum valor/premissa fabricado — base real (BCB), premissas sempre do usuário, saída sempre
  `SIMULATED`
- [x] DEFINE status → `✅ Complete (Designed)`

---

## 9. Handoff

Pronto para `/build .claude/sdd/features/DESIGN_DEBTLAB_SIMULATOR.md`.

---

## 10. Revision history

| Data | Versão | Mudança | Autor |
|---|---|---|---|
| 2026-09-07 | 1.0 | Criação a partir de `DEFINE_DEBTLAB_SIMULATOR.md`. Descoberta real (§0): fonte BCB SGS confirmada por chamada de API real (PIB série 4380, dívida/PIB série 13762); achado conceitual corrigido (`divida_consolidada` não é a base certa); achado de infra real (API read-only, CORS GET-only, dataset `control` já semanticamente correto). Fórmula reformulada para a equação padrão de razão dívida/PIB (D2), mais simples que o rascunho do `/define`. 5 decisões inline (D1–D5). Manifesto de 20 itens. Status → Ready for Build. | /design (Claude Sonnet 5) |
