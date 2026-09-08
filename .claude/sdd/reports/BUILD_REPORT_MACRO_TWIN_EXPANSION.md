# BUILD REPORT — MACRO_TWIN_EXPANSION

## Metadados

- **Feature:** MACRO_TWIN_EXPANSION
- **Fase:** 3 (Build)
- **Entrada:** `.claude/sdd/features/DESIGN_MACRO_TWIN_EXPANSION.md` (v1.0)
- **Branch:** `feature/macro-twin-expansion`
- **Data:** 2026-09-08
- **Status da build:** ✅ Completo (PR1 ingestão + PR2 endpoint de sugestão + PR3 hotfix de bug real
  de SQL/infra de teste de integração) — pronto para `/verify-spec`
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

### Achado #4 — bug real de produção: erro de sintaxe SQL na query YoY de `pib_mensal` (PR3, hotfix)

A primeira chamada real em produção a `GET /v1/simulations/debtlab/suggested-assumptions` (após o
deploy da PR2) retornou 500. `gcloud run services logs read` mostrou o traceback completo:
`google.api_core.exceptions.BadRequest: 400 ORDER BY clause expression references column
reference_date which is neither grouped nor aggregated`. Causa raiz: a query de YoY do PIB em
`bigquery_repo.py::suggested_assumptions()` colocava `ORDER BY reference_date DESC LIMIT 12` fora
dos parênteses do `SELECT` agregador (`AVG`/`STDDEV_SAMP`), em vez de dentro de uma subquery
intermediária que isola as 12 linhas mais recentes **antes** da agregação — a query irmã de SELIC
já tinha a estrutura de 2 níveis correta, usada como padrão de referência para a correção.
**Corrigido** com aninhamento explícito de 3 níveis (interna calcula YoY via `LAG`; intermediária
isola as 12 linhas não-nulas mais recentes via `ORDER BY`+`LIMIT`; externa agrega exatamente sobre
essas 12). Verificado contra BigQuery real (novo teste de integração, `§ Achado #4` abaixo) e,
após o deploy da PR3, contra o endpoint de produção: `HTTP 200`, `juros_nominal.mean≈0.1349`
(SELIC anualizada), `crescimento_nominal_pib.mean≈0.0716` (PIB YoY nominal) — valores em faixa
plausível.

**Causa raiz sistêmica identificada e corrigida junto:** `api/` nunca teve um teste de integração
contra BigQuery real antes desta feature — todos os testes anteriores usavam funções `run_query`
falsas que casam SQL por substring, que nunca chegam a parsear/executar SQL de verdade. Um erro de
sintaxe SQL não tinha como ser pego antes do deploy. Fechado nesta mesma PR (não uma decisão
adiada): `api/tests/integration/test_suggested_assumptions_bigquery.py` (novo, contra as tabelas
Gold já populadas, somente leitura, sem dataset isolado necessário), convenção de marker
`integration`/`addopts` em `api/pyproject.toml` (espelhando o padrão já existente em
`ingestion/pyproject.toml`), e `.github/workflows/ci.yml`: job `integration` estendido para também
disparar em mudanças de `api/` e rodar os testes de integração da API. PR #39, `ci-gate` verde
confirmou a nova etapa de CI funcionando (5m14s), squash-merged e deployado.

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
- **PR3 (hotfix, Achado #4):** `ruff check`/`format --check`/`mypy`/`pytest -q` limpos (47 passed +
  1 deselected). Novo teste de integração rodado manualmente contra `brasil2036-dev` real
  (`GCP_PROJECT=brasil2036-dev pytest -m integration`) — **PASS em 71.57s**. `ci-gate` do PR #39
  verde, incluindo a nova etapa `api integration tests against real BigQuery` no job `integration`
  (5m14s) — primeira execução real dessa etapa. Após squash-merge e deploy (`api-web.yml`,
  3m11s), `GET /v1/simulations/debtlab/suggested-assumptions` re-verificado ao vivo em produção:
  `HTTP 200` com valores reais (antes: `HTTP 500`).

---

## 4. Autonomous Decisions

| # | Decision Point | Options Considered | Chose | Rationale |
|---|----------------|--------------------|-------|-----------|
| 1 | Criar o fixture `pib_mensal_sample.json` que faltava, ou deixar a parametrização com só 4 séries | (a) parametrizar só sobre as séries que já tinham fixture; (b) criar o fixture faltante e cobrir as 5 | (b) | O DESIGN já previa cobertura das 5 séries; deixar `pib_mensal` de fora seria uma lacuna de teste real, não uma decisão deliberada. |
| 2 | Ordem de registro das rotas FastAPI | (a) registrar `/suggested-assumptions` depois de `/{scenario_id}` (ordem "natural" de leitura do arquivo); (b) antes | (b) | FastAPI casa por ordem de registro — (a) quebraria a rota nova silenciosamente (404 em vez do resultado real), achado confirmado por teste antes de qualquer deploy. |
| 3 | `data_class` da sugestão | (a) `observed` (copiado do molde mais próximo); (b) `estimated` | (b) | `ADR-028`: é uma derivação, não uma leitura direta de dado observado. |
| 4 | Após o bug real de SQL (Achado #4): corrigir só a query, ou também fechar a lacuna sistêmica de testes | (a) corrigir só `suggested_assumptions()` e seguir; (b) corrigir + adicionar infraestrutura de teste de integração real para `api/` (marker, CI, teste novo) | (b) | O mesmo padrão de bug (SQL/serialização que mocks não capturam) já tinha acontecido uma vez antes nesta sessão (`maximum_bytes_billed=None` no DEBTLAB_SIMULATOR) — 2 bugs reais em produção da mesma categoria era sinal de lacuna estrutural, não de azar; deixar sem correção estrutural teria permitido um 3º. |

---

## 5. Blockers / trabalho restante

Nenhum blocker. Backfill real das 3 séries novas contra `brasil2036-dev` **confirmado completo**
(reverificado ao vivo: `ipca_mensal`, `selic_mensal`, `cambio_usd_brl` retornam dado real e
`observed` em `/v1/metrics/{id}/national`; `suggested-assumptions` consome 12 meses reais de
`selic_mensal`/`pib_mensal` sem gaps).

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
| 2026-09-08 | 1.1 | PR3 (hotfix, Achado #4): 2º bug real de produção da sessão — erro de sintaxe SQL na query YoY de `pib_mensal` (`ORDER BY`/`LIMIT` fora dos parênteses do agregador), causando `HTTP 500` na primeira chamada real de `suggested-assumptions`. Corrigido com aninhamento SQL de 3 níveis. Causa raiz sistêmica fechada junto: `api/` nunca teve teste de integração contra BigQuery real — adicionado `api/tests/integration/`, marker `integration` em `api/pyproject.toml`, e etapa nova no job `integration` do `ci.yml`. PR #39 `ci-gate` verde (nova etapa validada em CI pela 1ª vez), squash-merged, deploy confirmado, endpoint re-verificado ao vivo (`HTTP 200`). Backfill real das 3 séries novas confirmado completo (não mais pendente). | /build (Claude Sonnet 5) |
