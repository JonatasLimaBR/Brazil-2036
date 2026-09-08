# BUILD REPORT — MACRO_TWIN_EXPANSION

## Metadados

- **Feature:** MACRO_TWIN_EXPANSION
- **Fase:** 3 (Build)
- **Entrada:** `.claude/sdd/features/DESIGN_MACRO_TWIN_EXPANSION.md` (v1.0)
- **Branch:** `feature/macro-twin-expansion`
- **Data:** 2026-09-08
- **Status da build:** ✅ Completo (PR1 ingestão + PR2 endpoint de sugestão) — pronto para
  `/verify-spec`
- **Próximo passo:** `/verify-spec` (sessão nova, read-only) → `/ship`

> Nota: assets do plugin SDD ausentes — relatório segue a lista de seções do skill `sdd-build`.

---

## 1. Task execution

### PR1 — Ingestão real de IPCA, SELIC e câmbio (BCB SGS)

| # | Arquivo | Ação | Nota |
|---|---|---|---|
| 1 | `ingestion/contracts/ipca_mensal.yaml` | Create | `allow_negative: true` — único entre as 3 séries desta fatia (achado real: mês de deflação) |
| 2 | `ingestion/contracts/selic_mensal.yaml` | Create | Série 4390 (mensal), não 432 (diária) |
| 3 | `ingestion/contracts/cambio_usd_brl.yaml` | Create | Série 3695 (mensal), não 1 (diária) |
| 4-9 | `ingestion/sql/{silver,gold}/{ipca_mensal,selic_mensal,cambio_usd_brl}.sql` | Create | Mesmo molde de `pib_mensal.sql`/`divida_bruta_pib.sql` |
| 10-12 | `ingestion/config/{ipca_mensal,selic_mensal,cambio_usd_brl}.yaml` | Create | `WideSeriesConfig` YAML, 1 metric_id cada |
| 13 | `ingestion/scripts/run_bcb_macro.py` | Modify | `_SERIES_CODES` ganha as 3 entradas novas |
| 14 | `ingestion/tests/integration/test_pipeline_bcb_macro_bigquery.py` | Modify | Refatorado para `pytest.mark.parametrize` sobre as 5 séries BCB agora (2 do DebtLab + 3 novas) — achado do build: faltava um fixture de `pib_mensal`, criado agora para completar a parametrização |
| 15 | `ingestion/tests/integration/fixtures/{ipca_mensal,selic_mensal,cambio_usd_brl,pib_mensal}_sample.json` | Create | Valores reais confirmados no `/design` |

### PR2 — Endpoint de sugestão de premissas para o DebtLab

| # | Arquivo | Ação | Nota |
|---|---|---|---|
| 16 | `api/src/api/config.yaml` | Modify | +`metric_tables` para as 3 séries novas |
| 17 | `api/src/api/models.py` | Modify | +`SuggestedAssumption`, `SuggestedAssumptionsResponse` (`data_class=estimated`, achado do build — ver `§2`) |
| 18 | `api/src/api/bigquery_repo.py` | Modify | +`suggested_assumptions()` — 2 queries SQL (SELIC anualizada, PIB YoY) sobre Gold real |
| 19 | `api/src/api/main.py` | Modify | +`GET /v1/simulations/debtlab/suggested-assumptions` — registrado **antes** de `/{scenario_id}` (achado real de roteamento, `§2`); `POST` inalterado |
| 20 | `api/tests/test_suggested_assumptions.py` | Create | Cálculo contra dado sintético + teste explícito de que a rota não é engolida pela `/{scenario_id}` |
| 21 | `docs/adrs/ADR-060-macro-twin-suggested-assumptions.md` | Create | Formaliza D1-D3 do DESIGN |
| 22 | `INDEX.md` | Modify | +ADR-060 |
| 23 | `api/openapi/openapi.json` + `web/src/api-client/schema.d.ts` | Modify (regenerado) | Ambos regenerados nesta mesma PR (lição do `DEBTLAB_SIMULATOR`: `web-check` roda sempre que `openapi.json` muda) |

---

## 2. Achados técnicos durante o build (não previstos em detalhe pelo DESIGN)

### Achado #1 — faltava o fixture de `pib_mensal` para completar a parametrização

O DESIGN previa parametrizar o teste de integração sobre as 5 séries (2 do DebtLab + 3 novas), mas
o `DEBTLAB_SIMULATOR` só tinha criado um teste/fixture para `divida_bruta_pib`, não para
`pib_mensal`. Corrigido: fixture `pib_mensal_sample.json` criado agora (valores reais já
confirmados no `/design` do `DEBTLAB_SIMULATOR`), completando a cobertura real das 5 séries.

### Achado #2 — risco real de roteamento: `/{scenario_id}` engolindo `/suggested-assumptions`

FastAPI casa rotas na ordem de registro. `GET /v1/simulations/debtlab/{scenario_id}` já existia
(shipado no `DEBTLAB_SIMULATOR`) — se o endpoint novo fosse registrado depois dele, uma chamada a
`/v1/simulations/debtlab/suggested-assumptions` seria interpretada como `scenario_id =
"suggested-assumptions"` e cairia no handler errado (`get_debtlab_scenario`), retornando 404 em
vez do resultado real. **Corrigido**: `GET /v1/simulations/debtlab/suggested-assumptions`
registrado **antes** de `/{scenario_id}` em `main.py`. Teste de regressão específico adicionado
(`test_endpoint_returns_suggestion_not_shadowed_by_scenario_route`, com um `_StubRepo` que levanta
`AssertionError` se `get_debtlab_scenario` for chamado com `scenario_id="suggested-assumptions"`).

### Achado #3 — `data_class` correto para a sugestão é `estimated`, não `observed`

Rascunho inicial do modelo usava `DataClass.observed` por padrão (copiado do molde de
`NationalMetricResponse`). Corrigido durante a implementação: a sugestão é uma **derivação**
determinística de dado observado (composição/YoY), não uma leitura direta — `ADR-028` classifica
isso como `estimated`. Nenhum código de produção chegou a usar o valor errado (corrigido antes de
qualquer commit).

---

## 3. Verification results

- **Ingestão:** `ruff check`/`format --check`/`mypy` limpos (24 arquivos fonte); `pytest` — 110
  passed, 8 deselected (integration, agora 5 casos parametrizados).
- **Integration real contra `brasil2036-dev`:** `test_bcb_series_pipeline_against_bigquery`
  parametrizado — **5/5 PASS** (`pib_mensal`, `divida_bruta_pib`, `ipca_mensal`, `selic_mensal`,
  `cambio_usd_brl`), datasets `citest_<run>_bcbmacro_*` isolados, limpos ao final. Confirma
  `status="ok"`, 3 linhas Gold cada, valor real do mês mais recente batendo exatamente contra a
  API do BCB (82.51% dívida/PIB, R$1.167.869.000.000 PIB, 0.07% IPCA, 0.21% SELIC, R$5.1810
  câmbio).
- **API:** `ruff check`/`format --check`/`mypy` limpos (8 arquivos fonte); `pytest` — 47 passed (6
  novos: 3 do cálculo de sugestão + 2 do endpoint + 1 de rota, 0 regressão nos 41 pré-existentes,
  incluindo os testes do `POST /v1/simulations/debtlab` — `AT6` confirmado).
- **`web/`:** `npm run gen:client` + `typecheck` (`astro check`, 0 erros) + `build` verdes contra o
  `openapi.json` regenerado.

---

## 4. Autonomous Decisions

| # | Decision Point | Options Considered | Chose | Rationale |
|---|----------------|--------------------|-------|-----------|
| 1 | Criar o fixture `pib_mensal_sample.json` que faltava, ou deixar a parametrização com só 4 séries | (a) parametrizar só sobre as séries que já tinham fixture; (b) criar o fixture faltante e cobrir as 5 | (b) | O DESIGN já previa cobertura das 5 séries; deixar `pib_mensal` de fora seria uma lacuna de teste real, não uma decisão deliberada. |
| 2 | Ordem de registro das rotas FastAPI | (a) registrar `/suggested-assumptions` depois de `/{scenario_id}` (ordem "natural" de leitura do arquivo); (b) antes | (b) | FastAPI casa por ordem de registro — (a) quebraria a rota nova silenciosamente (404 em vez do resultado real), achado confirmado por teste antes de qualquer deploy. |
| 3 | `data_class` da sugestão | (a) `observed` (copiado do molde mais próximo); (b) `estimated` | (b) | `ADR-028`: é uma derivação, não uma leitura direta de dado observado. |

---

## 5. Blockers / trabalho restante

Nenhum blocker. Backfill real das 3 séries novas contra `brasil2036-dev` (fora do dataset
`citest_*` isolado do teste de integração) ainda não executado — será feito e confirmado antes do
`/ship`, mesmo padrão de toda fatia de dado anterior.

---

## 6. Status transitions

| Arquivo | Status | Próximo |
|---|---|---|
| `DEFINE_MACRO_TWIN_EXPANSION.md` | ✅ Complete (Built) | `/verify-spec` → `/ship` |
| `DESIGN_MACRO_TWIN_EXPANSION.md` | ✅ Complete (Built) | idem |

---

## 7. Revision history

| Data | Versão | Mudança | Autor |
|---|---|---|---|
| 2026-09-08 | 1.0 | Build completo: PR1 (ingestão real de IPCA/SELIC/câmbio) + PR2 (endpoint de sugestão de premissas para o DebtLab, ADR-060). 3 achados reais durante o build (fixture faltante de `pib_mensal`; risco real de roteamento FastAPI corrigido antes do deploy; `data_class` corrigido para `estimated`). Integration test real contra `brasil2036-dev` PASS (5/5 séries). `typecheck`/`lint`/`unit` verdes em ambos os pacotes + `web/`, 0 regressão. | /build (Claude Sonnet 5) |
