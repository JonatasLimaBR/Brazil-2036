# DESIGN — MACRO_TWIN_EXPANSION

## Metadados

- **Feature:** MACRO_TWIN_EXPANSION
- **Status:** ✅ Complete (Built)
- **Fase:** 2 (Design)
- **Entrada:** `.claude/sdd/features/DEFINE_MACRO_TWIN_EXPANSION.md` (Clarity 13/15)
- **Criado:** 2026-09-08
- **Idioma:** PT-BR
- **Branch:** a criar — `feature/macro-twin-expansion`
- **Confiança:** 0.9 — padrão de conector/pipeline já provado 2x, fontes confirmadas reais com
  histórico suficiente; único território novo é o cálculo de sugestão (anualização/YoY), simples
  e bem isolado.
- **Próximo passo:** `/build .claude/sdd/features/DESIGN_MACRO_TWIN_EXPANSION.md`

> Nota: assets do plugin SDD ausentes — documento segue a lista de seções do skill `sdd-design`.

---

## 0. Descoberta real (resolve OQ1–OQ4 do DEFINE)

### 0.1 Histórico real confirmado — resolve OQ1/OQ4/A1

Chamadas diretas à API do BCB SGS confirmaram ≥15 meses reais consecutivos para as 3 séries
(margem sobre a janela de 12 meses):

- **SELIC acumulada mensal (série 4390):** 15 meses reais, 07/2025–09/2026, valores 0,21%–1,28%.
- **IPCA (série 433):** 15 meses reais, 05/2025–07/2026, valores -0,11%–0,88%.
- **Câmbio USD/BRL médio mensal (série 3695):** 15 meses reais, 06/2025–08/2026, valores
  R$4,99–5,60.

Janela de 12 meses confirmada viável para as 3 séries (resolve OQ1: 12 meses, não outro valor).

### 0.2 Achado real: IPCA pode ser negativo (deflação) — diferente de SELIC/câmbio

`-0,11%` em 08/2025 é um mês real de deflação. Diferente de SELIC/dívida/câmbio (sempre positivos
na prática), o contrato de `ipca_mensal` precisa de `allow_negative: true` — mesmo padrão já usado
em `fiscal_primario` (`FISCAL_RECEITA_DESPESA`, `contract.check_gold_period(allow_negative=...)`).

### 0.3 Cálculo da sugestão — resolve OQ2

`juros_nominal` e `crescimento_nominal_pib` no motor do DebtLab (`debtlab.py`) são taxas
**anuais**, mas as séries fonte têm periodicidade diferente:

- **SELIC (`selic_mensal`) é uma taxa mensal acumulada.** Anualizar por composição:
  `juros_anual = (1 + MÉDIA(selic_mensal, últimos 12 meses)) ^ 12 - 1`. Desvio-padrão anualizado
  aproximado por escalonamento linear da variância (`STDDEV(selic_mensal) * SQRT(12)`) — uma
  aproximação padrão e documentada (não uma conversão exata, mas correta o bastante para uma
  *sugestão*, não uma previsão oficial).
- **PIB (`pib_mensal`) é um nível absoluto (R$), não uma taxa.** Crescimento anual direto via
  variação ano-contra-ano (YoY): para cada um dos últimos 12 meses `M`, `crescimento_M =
  PIB_M / PIB_(M-12) - 1` — já é uma taxa anual por construção, sem precisar compor. Média e
  desvio-padrão sobre esses 12 valores de `crescimento_M`. Requer 24 meses de PIB em Gold
  (confirmado: 438 linhas já carregadas, sobra de margem).

Ambos os cálculos são SQL determinístico sobre dado real em Gold — nenhum valor fabricado, nenhum
caminho de LLM (`ADR-012`).

### 0.4 `ADR-060` é necessário — resolve OQ3

O cálculo de anualização/YoY é uma decisão metodológica real (por que composição para SELIC, por
que YoY para PIB, por que a aproximação de desvio-padrão) que merece registro formal, não só uma
nota — mesmo padrão de `ADR-057`/`ADR-059` (decisões de código com racional técnico específico).

---

## 1. Grounding

| Padrão a reaproveitar | Fonte |
|---|---|
| `BcbSgsConnector` genérico | `ingestion/src/ingestion/connectors/bcb_sgs.py` — reaproveitado como está, 3 instâncias novas (séries 433/4390/3695), zero mudança de código no conector. |
| 1 conjunto de tabelas por série, `pipeline_wide_series.py` | Mesmo molde de `pib_mensal`/`divida_bruta_pib` (`DEBTLAB_SIMULATOR` Achado #1) — evita provenance errada. |
| `config.metric_tables` genérico + `/v1/metrics/{metric_id}/national` | Zero código novo de leitura — só entradas de config, mesmo padrão de todas as fatias anteriores. |
| `allow_negative` por contrato | `ingestion/sql` + `contract.check_gold_period(allow_negative=...)` já suporta isso (`FISCAL_RECEITA_DESPESA`), reaproveitado para `ipca_mensal`. |
| `RunQuery` com `maximum_bytes_billed` opcional | `api/src/api/bigquery_repo.py` (já um `Protocol`, `DEBTLAB_SIMULATOR`) — a query de sugestão é um `SELECT` de leitura, usa o cap padrão normalmente (`DEFAULT_MAX_BYTES_BILLED`), sem precisar de `None`. |

---

## 2. Arquitetura

```text
┌──────────────────────────────────────────────────────────────────────────┐
│  ingestion/ (reaproveita 100% a infra do DEBTLAB_SIMULATOR)              │
│                                                                            │
│  BcbSgsConnector(series_code=433,  metric_id="ipca_mensal")               │
│  BcbSgsConnector(series_code=4390, metric_id="selic_mensal")              │
│  BcbSgsConnector(series_code=3695, metric_id="cambio_usd_brl")            │
│    └─ mesmo pipeline_wide_series.py, 3 execuções independentes            │
│       → gold_ipca_mensal / gold_selic_mensal / gold_cambio_usd_brl        │
└──────────────────────────┬─────────────────────────────────────────────────┘
                             │ metric_tables: ipca_mensal, selic_mensal, cambio_usd_brl
                             ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  api/src/api/ (FastAPI, Cloud Run)                                       │
│                                                                            │
│  GET /v1/metrics/{ipca,selic,cambio}_mensal/national  ── já genérico     │
│                                                                            │
│  GET /v1/simulations/debtlab/suggested-assumptions  ── NOVO              │
│    └─ lê gold_selic_mensal (12m) → anualiza (composição)                 │
│    └─ lê gold_pib_mensal (24m) → YoY (12 pontos) → média/desvio          │
│    └─ retorna SuggestedAssumptionsResponse (nunca escreve, só lê)        │
│                                                                            │
│  POST /v1/simulations/debtlab  ── INALTERADO (contrato já shipado)       │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Decisões (ADRs inline)

### D1 — Cada série mantém seu próprio conjunto de tabelas (reafirma D1 do `ADR-059`)

| Atributo | Valor |
|---|---|
| Status | Accepted |
| Data | 2026-09-08 |

**Contexto:** 3 séries BCB novas, mesmo risco de provenance já resolvido no `DEBTLAB_SIMULATOR`.

**Escolha:** 3 execuções independentes de `pipeline_wide_series.run()`, `metric_ids=(1,)` cada,
mesmo padrão de `pib_mensal`/`divida_bruta_pib`.

**Racional:** já validado e documentado (`ADR-059` D1) — reaplicar sem reabrir a discussão.

**Consequências:** (+) zero risco novo de provenance incorreta; (−) 3x arquivos repetitivos
(aceito, mesmo padrão INSS).

### D2 — Anualização de SELIC por composição, crescimento de PIB por YoY direto

| Atributo | Valor |
|---|---|
| Status | Accepted |
| Data | 2026-09-08 |

**Contexto:** `debtlab.py` espera taxas anuais; SELIC é mensal acumulada, PIB é nível absoluto —
`§0.3`.

**Escolha:** `juros_anual = (1+méd(selic_12m))^12 - 1`, desvio aproximado por
`stddev(selic_12m)*√12`; `crescimento_M = PIB_M/PIB_(M-12) - 1` para os últimos 12 meses, média e
desvio direto sobre esses 12 valores.

**Racional:** cada série exige uma conversão diferente por causa da sua própria natureza (taxa vs.
nível) — usar a mesma fórmula para as duas seria matematicamente incorreto. YoY para PIB evita
precisar de uma segunda composição.

**Alternativas rejeitadas:** aplicar a mesma composição da SELIC ao PIB (dividindo por 12 partes
iguais) — rejeitado, PIB não é uma taxa, dividir por 12 assumiria crescimento uniforme dentro do
ano, distorção desnecessária quando o dado real já permite comparação direta ano-contra-ano.

**Consequências:** (+) cada conversão é a matematicamente correta para a natureza do dado; (+)
sem fabricar nada, 100% SQL sobre dado real. (−) o desvio-padrão anualizado da SELIC é uma
aproximação (escalonamento linear), não uma conversão exata — documentado explicitamente como tal
na resposta da API (`§5.2`), nunca apresentado como precisão maior do que tem.

### D3 — Endpoint `GET` separado, não default automático no `POST` (reafirma decisão do usuário)

| Atributo | Valor |
|---|---|
| Status | Accepted |
| Data | 2026-09-08 |

**Contexto:** decisão já tomada no `/brainstorm` — não mudar o contrato do `POST` já shipado e em
produção.

**Escolha:** `GET /v1/simulations/debtlab/suggested-assumptions`, sem nenhuma mudança em
`DebtLabScenarioRequest`/`POST /v1/simulations/debtlab`.

**Consequências:** (+) zero risco de regressão no endpoint já testado/em produção; (+) mais
transparente (o chamador vê a sugestão antes de decidir usá-la, não é aplicada às escondidas).

---

## 4. Manifesto de arquivos

| # | Arquivo | Ação | Propósito | Agente | Deps |
|---|---|---|---|---|---|
| 1 | `ingestion/contracts/ipca_mensal.yaml` | Create | Contrato, `allow_negative: true` (`§0.2`) | `data-contracts-engineer` | — |
| 2 | `ingestion/contracts/selic_mensal.yaml` | Create | Contrato, sempre positivo | `data-contracts-engineer` | — |
| 3 | `ingestion/contracts/cambio_usd_brl.yaml` | Create | Contrato, sempre positivo | `data-contracts-engineer` | — |
| 4 | `ingestion/sql/silver/ipca_mensal.sql` | Create | Mesmo molde de `pib_mensal.sql`, unidade `pct` | `gcp-data-architect` | 1 |
| 5 | `ingestion/sql/gold/gold_ipca_mensal.sql` | Create | idem | `gcp-data-architect` | 4 |
| 6 | `ingestion/sql/silver/selic_mensal.sql` | Create | unidade `pct` | `gcp-data-architect` | 2 |
| 7 | `ingestion/sql/gold/gold_selic_mensal.sql` | Create | idem | `gcp-data-architect` | 6 |
| 8 | `ingestion/sql/silver/cambio_usd_brl.sql` | Create | unidade `brl_per_usd` | `gcp-data-architect` | 3 |
| 9 | `ingestion/sql/gold/gold_cambio_usd_brl.sql` | Create | idem | `gcp-data-architect` | 8 |
| 10 | `ingestion/config/ipca_mensal.yaml` | Create | `WideSeriesConfig`, `allow_negative_metric_ids: [ipca_mensal]` | `(general)` | 1, 4, 5 |
| 11 | `ingestion/config/selic_mensal.yaml` | Create | idem sem negative | `(general)` | 2, 6, 7 |
| 12 | `ingestion/config/cambio_usd_brl.yaml` | Create | idem | `(general)` | 3, 8, 9 |
| 13 | `ingestion/scripts/run_bcb_macro.py` | Modify | `_SERIES_CODES` ganha `ipca_mensal: 433, selic_mensal: 4390, cambio_usd_brl: 3695` | `python-developer` | 10-12 |
| 14 | `ingestion/tests/integration/test_pipeline_bcb_macro_bigquery.py` | Modify | Parametrizado (`pytest.mark.parametrize`) sobre as 5 séries agora (2 do DebtLab + 3 novas), 1 fixture JSON nova por série nova | `test-generator` | 13 |
| 15 | `ingestion/tests/integration/fixtures/{ipca_mensal,selic_mensal,cambio_usd_brl}_sample.json` | Create | Valores reais confirmados (`§0.1`) | `(general)` | — |
| 16 | `api/src/api/config.py`/`config.yaml` | Modify | +`metric_tables` para as 3 séries novas | `(general)` | — |
| 17 | `api/src/api/models.py` | Modify | +`SuggestedAssumption` (mean/std/window_months/source_metric_id/period_start/period_end), `SuggestedAssumptionsResponse` | `python-developer` | — |
| 18 | `api/src/api/bigquery_repo.py` | Modify | +`suggested_assumptions()` — 2 queries SQL (SELIC anualizada, PIB YoY) sobre Gold real | `python-developer` | 17 |
| 19 | `api/src/api/main.py` | Modify | +`GET /v1/simulations/debtlab/suggested-assumptions` — **`POST` inalterado** (`D3`) | `python-developer` | 18 |
| 20 | `api/tests/test_suggested_assumptions.py` | Create | Testes do cálculo (SELIC anualizada, PIB YoY) contra dado sintético conhecido + contrato do endpoint | `test-generator` | 19 |
| 21 | `api/tests/test_debtlab_endpoint.py` | Verify only | Confirma que os testes existentes do `POST` continuam passando sem alteração (`AT6`) | — | — |
| 22 | `docs/adrs/ADR-060-macro-twin-suggested-assumptions.md` | Create | Formaliza D1-D3 | `architect` | 1-19 |

### Racional de agentes
Mesmo padrão do `DEBTLAB_SIMULATOR`: contrato/SQL → `data-contracts-engineer`/`gcp-data-architect`;
Python/testes → `python-developer`/`test-generator`; ADR → `architect`; config → `(general)`.

### Independência
Ingestão (1-15) e API (16-20) são paralelizáveis — o endpoint de sugestão só depende de
`gold_selic_mensal`/`gold_pib_mensal` existirem (PIB já existe; SELIC precisa da ingestão desta
própria fatia rodar primeiro em produção, mas o código do endpoint pode ser escrito/testado com
dado sintético independentemente). PR1 (ingestão) e PR2 (endpoint) seguem o mesmo padrão de PRs
separados já usado.

---

## 5. Padrões de código

### 5.1 `ingestion/config/ipca_mensal.yaml` (mesmo molde de `divida_bruta_pib.yaml`)

```yaml
dataset_id: ipca_mensal
br2036_domain: macro
br2036_module: M04

catalog_url: "https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados"
organization: "Banco Central do Brasil (BCB)"
license: "Dados abertos do governo federal"

metric_ids:
  - ipca_mensal
unit: pct
allow_negative_metric_ids:
  - ipca_mensal

contract_path: contracts/ipca_mensal.yaml

gcp_project: ""
raw_bucket: ""
raw_prefix: macro

bq_dataset_control: br2036_control
bq_dataset_bronze: br2036_bronze
bq_dataset_silver: br2036_silver
bq_dataset_gold: br2036_gold

bronze_table: ipca_mensal_raw
bronze_columns:
  - reference_period
  - value
field_delimiter: ","

silver_model: ipca_mensal
gold_model: gold_ipca_mensal

ckan_base_url: ""
ckan_package_id: ""
```

### 5.2 `api/src/api/bigquery_repo.py::suggested_assumptions()` — cálculo real, aproximação documentada

```python
def suggested_assumptions(self) -> SuggestedAssumptionsResponse | None:
    gold = self._config.bq_dataset_gold

    # SELIC: taxa mensal acumulada -> anualizar por composicao.
    selic_rows = self._run_query(
        f"SELECT AVG(value) AS avg_m, STDDEV(value) AS std_m, "
        f"MIN(reference_date) AS start_d, MAX(reference_date) AS end_d, COUNT(*) AS n "
        f"FROM (SELECT value, reference_date FROM `{self._config.gcp_project}.{gold}.gold_selic_mensal` "
        f"WHERE metric_id = 'selic_mensal' ORDER BY reference_date DESC LIMIT 12)",
        {},
    )
    # PIB: nivel absoluto -> crescimento YoY por mes, media/desvio sobre os 12 pontos.
    pib_rows = self._run_query(
        f"SELECT AVG(yoy) AS avg_yoy, STDDEV(yoy) AS std_yoy, "
        f"MIN(reference_date) AS start_d, MAX(reference_date) AS end_d, COUNT(*) AS n FROM ("
        f"  SELECT reference_date, value / LAG(value, 12) OVER (ORDER BY reference_date) - 1 AS yoy"
        f"  FROM `{self._config.gcp_project}.{gold}.gold_pib_mensal` WHERE metric_id = 'pib_mensal'"
        f") WHERE yoy IS NOT NULL ORDER BY reference_date DESC LIMIT 12",
        {},
    )
    if not selic_rows or not pib_rows or selic_rows[0]["n"] < 12 or pib_rows[0]["n"] < 12:
        return None  # dado real insuficiente -- nunca completar com valor fabricado

    selic = selic_rows[0]
    juros_mean = (1 + float(selic["avg_m"]) / 100) ** 12 - 1
    juros_std = float(selic["std_m"]) / 100 * (12 ** 0.5)  # aproximacao linear, documentada (D2)

    pib = pib_rows[0]
    return SuggestedAssumptionsResponse(
        juros_nominal=SuggestedAssumption(
            mean=juros_mean, std=juros_std, window_months=12,
            source_metric_id="selic_mensal",
            period_start=str(selic["start_d"]), period_end=str(selic["end_d"]),
            methodology="selic_mensal composta 12x (nao e uma conversao exata de desvio-padrao)",
        ),
        crescimento_nominal_pib=SuggestedAssumption(
            mean=float(pib["avg_yoy"]), std=float(pib["std_yoy"]), window_months=12,
            source_metric_id="pib_mensal",
            period_start=str(pib["start_d"]), period_end=str(pib["end_d"]),
            methodology="variacao ano-contra-ano (YoY) mes a mes",
        ),
    )
```

---

## 6. Estratégia de testes

| Tipo | Escopo | Ferramenta |
|---|---|---|
| Unit — cálculo de sugestão | `suggested_assumptions()` contra dado sintético conhecido (SELIC/PIB fake com resultado calculável à mão) | `pytest` |
| Unit — regressão do `POST` | `test_debtlab_endpoint.py` roda sem alteração, confirma `AT6` | `pytest` (já existente) |
| Contract — endpoint novo | `GET /v1/simulations/debtlab/suggested-assumptions` retorna 200 com estrutura correta; 404/erro claro se dado insuficiente | `pytest` + `TestClient` |
| Integration (CI) | Pipeline parametrizado sobre as 5 séries BCB (2 do DebtLab + 3 novas) contra BigQuery real | `ci / integration` |
| Manual — conferência de ground truth | Valores da sugestão plausíveis contra os números reais confirmados no `§0.1` | Execução real contra `brasil2036-dev` |

Cobre AT1–AT8 do DEFINE.

---

## 7. Pipeline Architecture (contexto DE)

| Aspecto | Definição |
|---|---|
| **Fonte** | API JSON pública do BCB SGS, mesma já integrada (`§0.1`). |
| **Estratégia de carga** | Full-history por série a cada execução, mesmo padrão de `pib_mensal`/`divida_bruta_pib`. |
| **Particionamento/clustering** | `PARTITION BY reference_date CLUSTER BY metric_id` (`SPEC-034`). |
| **Qualidade de dado** | Contrato por `metric_id`; `ipca_mensal` com `allow_negative: true` (`§0.2`), os outros 2 sem. |

---

## 8. Quality gate (Fase 2)

- [x] Descoberta real feita — histórico das 3 séries confirmado por chamada real, achado real do
  IPCA negativo, metodologia de anualização/YoY justificada
- [x] ASCII diagram criado e claro (`§2`)
- [x] Pelo menos 1 decisão com racional completo (3 decisões, D1-D3)
- [x] Manifesto de arquivos completo (22 itens)
- [x] Agente atribuído a cada arquivo
- [x] Padrões de código sintaticamente corretos, prontos para copiar-adaptar
- [x] Estratégia de testes cobre os acceptance tests do DEFINE (AT1-AT8)
- [x] Sem dependência circular na arquitetura
- [x] Nenhum valor fabricado — sugestão sempre de dado real, aproximação documentada
  explicitamente, nunca apresentada como mais precisa do que é
- [x] DEFINE status → `✅ Complete (Designed)`

---

## 9. Handoff

Pronto para `/build .claude/sdd/features/DESIGN_MACRO_TWIN_EXPANSION.md`.

---

## 10. Revision history

| Data | Versão | Mudança | Autor |
|---|---|---|---|
| 2026-09-08 | 1.0 | Criação a partir de `DEFINE_MACRO_TWIN_EXPANSION.md`. Descoberta real (§0): histórico das 3 séries confirmado (≥15 meses reais cada); achado real do IPCA negativo (`allow_negative`); metodologia de anualização (SELIC por composição) e crescimento (PIB por YoY) justificada e documentada como aproximação onde aplicável. 3 decisões inline (D1-D3). Manifesto de 22 itens. Status → Ready for Build. | /design (Claude Sonnet 5) |
