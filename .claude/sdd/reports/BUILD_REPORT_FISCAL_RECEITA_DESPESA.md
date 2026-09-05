# BUILD REPORT — FISCAL_RECEITA_DESPESA

## Metadados

- **Feature:** FISCAL_RECEITA_DESPESA
- **Fase:** 3 (Build)
- **Entrada:** `.claude/sdd/features/DESIGN_FISCAL_RECEITA_DESPESA.md` (v1.0)
- **Branch:** PR1 `feature/fiscal-receita-despesa` (merged, #15) · PR2 `feature/fiscal-receita-despesa-pr2` (API+web)
- **Data:** 2026-09-05
- **Status da build:** ✅ PR1+PR2 completos — backfill real pendente de confirmação do usuário
- **Próximo passo:** `/verify-spec` → `/ship` (após confirmar/rodar o backfill real, ou fechar o escopo sem ele, mesmo padrão das 2 fatias anteriores)

> Assets do plugin SDD ausentes — relatório segue a lista de seções do skill `sdd-build`.

---

## 1. Task execution (PR1 — espinha de dados)

| # | Arquivo | Ação | Nota |
|---|---|---|---|
| 1 | `docs/adrs/ADR-056-fiscal-uniao-wide-series-ingestion.md` | Create | Formaliza D1-D11 |
| 2 | `ingestion/src/ingestion/connectors/fiscal_uniao.py` | Create | Conector + `discover_resource`/`build_default_connector` (refinamento: separado de `FiscalUniaoConnector` para testabilidade via `file://`, mesmo padrão do `InssEmitidosConnector`) |
| 3 | `ingestion/tests/test_fiscal_uniao_connector.py` | Create | 12 testes: discovery, `file://`, validate, pivot, erro de rótulo ausente |
| 4 | `ingestion/src/ingestion/contract.py` | Modify | `check_gold_period(..., allow_negative: bool = False)` (D10 — achado crítico) |
| 5 | `ingestion/tests/test_contract.py` | Modify | +3 testes: rejeita negativo por padrão, aceita com `allow_negative=True`, ainda pega nulo |
| 6 | `ingestion/src/ingestion/provenance.py` | Modify | `reference_date: dt.date \| None = None` (D9) |
| 7 | `ingestion/tests/test_provenance.py` | Modify | +1 teste: escopo por `metric_id` inteiro quando `None` |
| 8 | `ingestion/src/ingestion/pipeline_wide_series.py` | Create | Orquestrador novo (D8): download 1x → RAW original (D6) → RAW CSV pivotado → Bronze whole-table → Silver/Gold → provenance por `metric_id` |
| 9 | `ingestion/tests/test_pipeline_wide_series.py` | Create | 5 testes: happy path (incl. primário negativo), 2 objetos RAW, no-op, quarentena, whole-table rebuild |
| 10 | `ingestion/contracts/fiscal_uniao.yaml` | Create | Schema + nota sobre `allow_negative` por `metric_id` |
| 11 | `ingestion/sql/silver/fiscal_uniao.sql` | Create | Pivot + conversão R$ milhões→R$ (D7) |
| 12 | `ingestion/sql/gold/gold_fiscal_uniao.sql` | Create | 1 tabela, 3 `metric_id`s (D2) |
| 13 | `ingestion/config/fiscal_uniao.yaml` | Create | Config do dataset |
| 14 | `ingestion/tests/integration/fixtures/fiscal_uniao_sample.xlsx` | Create | 2 meses (1 déficit, 1 superávit) |
| 15 | `ingestion/tests/integration/test_pipeline_fiscal_bigquery.py` | Create | `@pytest.mark.integration` — prova `allow_negative` contra BigQuery real |
| 16 | `INDEX.md` | Modify | +ADR-056 |
| 17 | `ingestion/src/ingestion/bronze.py` | Modify | `load(..., columns=BRONZE_COLUMNS, field_delimiter=";")` — generalização não prevista no DESIGN, achado durante o build (ver §4) |
| 18 | `ingestion/tests/test_bronze_partition.py` | Modify | +2 testes: default = shape original da dívida; custom columns não hardcoded |
| 19 | `ingestion/scripts/run_fiscal_uniao.py` | Create | Driver manual de produção, mesmo padrão de `run_backfill.py` (não estava no manifesto do DESIGN, necessário para o dataset ter um ponto de entrada real) |

## 1b. Task execution (PR2 — apresentação)

| # | Arquivo | Ação | Nota |
|---|---|---|---|
| 20 | `api/src/api/config.yaml` | Modify | +3 entradas em `metric_tables` → `gold_fiscal_uniao` (D11) — zero mudança em `main.py`/`bigquery_repo.py`, confirmado |
| 21 | `api/tests/test_bigquery_repo.py` | Modify | +3 testes: valor negativo aceito, 3 `metric_id`s compartilhando 1 tabela, não-regressão dívida+INSS |
| 22 | `api/tests/test_endpoints.py` | Modify | +1 teste: rota aceita `fiscal_primario` negativo ponta a ponta |
| 23 | `web/src/fiscal.ts` | Create | Módulo M02: "Receita líquida" (D4), "Despesa total", "Resultado primário" (com qualificador "(déficit)" quando negativo) |
| 24 | `web/src/main.ts` | Modify | `void renderFiscalModule();` |
| 25 | `web/index.html` | Modify | +`<section id="fiscal-module">` + `<h2>Fiscal &amp; DebtLab</h2>` |
| 26 | `web/src/styles.css` | Modify | Reaproveita `.inss-module`/`.inss-number`/`.inss-label` para `.fiscal-*` (seletores combinados, sem duplicar CSS) |
| 27 | `web/tests/e2e/card.spec.ts` | Modify | +1 suite M02; seletor de card da dívida já corrigido (PR #14) mantido escopado a `#card` |

---

## 2. Descoberta real durante o build (confirma/refina o DESIGN)

Nenhuma descoberta nova de dado real ocorreu durante o build (a descoberta do arquivo RTN e do
achado crítico D10 já aconteceu na Fase 2, `/design`, com o arquivo real baixado e inspecionado —
ver `DESIGN_FISCAL_RECEITA_DESPESA.md §0`). O que o build encontrou foi **2 achados técnicos de
código** que o DESIGN não havia antecipado no nível de detalhe de implementação:

### achado #1 — `bronze.load()` não era genérico como o DESIGN assumiu

O DESIGN (§1 Grounding) descreveu `bronze.load()` como reaproveitável ("CREATE OR REPLACE —
seguro aqui"), mas a implementação real tinha as colunas `UF, ANO, VALOR` e o delimitador `;`
**hardcoded no corpo da função** (não parametrizados, ao contrário de `load_partition()`, que já
aceitava `columns`/`field_delimiter`). Corrigido generalizando `load()` da mesma forma, com
default igual ao shape original da dívida — zero mudança de comportamento para o caller existente
(coberto por teste de regressão explícito, item 18).

### achado #2 — separação `discover_resource`/`FiscalUniaoConnector` para testabilidade

O DESIGN não especificou a interface exata do conector. Ao escrever o teste de integração
(precisa rodar sem rede, via `file://`, mesmo padrão do `InssEmitidosConnector`), ficou claro que
o conector deveria receber um `CkanResource` já resolvido (não fazer a chamada CKAN internamente
em `discover()`) — replicando exatamente a separação de responsabilidades já usada pelos 3
conectores do INSS. `discover_resource()` (função módulo, testável isolada) resolve o recurso via
`package_show`; `build_default_connector()` amarra os dois para uso em produção
(`run_fiscal_uniao.py`).

---

## 3. Verification results

### PR1 (ingestion)
- `ruff check .` — PASS (0 issues)
- `ruff format --check .` — PASS
- `mypy src` (strict) — PASS, 23 arquivos-fonte, 0 erros
- `pytest -q -m "not integration"` — **92 passed**, 3 deselected (integration)
- `pytest tests/integration/test_pipeline_fiscal_bigquery.py -m integration` — **skipped** (sem
  `GCP_PROJECT`; roda de verdade só no gate `integration` do `ci.yml`, mesmo padrão das 2 fatias
  anteriores)

### PR2 (api + web)
- `ruff check .` (api) — PASS
- `mypy src` (api, strict) — PASS, 5 arquivos-fonte, 0 erros
- `pytest -q` (api) — **20 passed** (16 → 20, +4 novos)
- `npm run typecheck` (web) — PASS
- `npm run build` (web) — PASS
- `npm run e2e` (web), rodado localmente com `VITE_API_URL` apontando para a API real de produção
  (`https://br2036-api-gzt6fzwoda-rj.a.run.app`) — **4/4 passed**, incluindo a nova suite do
  módulo M02 (degrada corretamente para "Indisponível", já que nenhum backfill real rodou ainda
  para `fiscal_receita`/`fiscal_despesa`/`fiscal_primario`)

**Nenhum backfill real contra `brasil2036-dev` foi executado nesta sessão de build** — o
mecanismo está provado via unit tests + (quando rodar no CI) o gate `integration` contra BigQuery
real com a fixture de 2 meses. Rodar o backfill real completo (356 meses × 3 métricas) é uma
decisão de custo/tempo que, seguindo o padrão já estabelecido nas 2 fatias anteriores, deve ser
confirmada explicitamente pelo usuário antes de executar.

---

## 4. Autonomous Decisions

| # | Decision Point | Options Considered | Chose | Rationale |
|---|----------------|--------------------|-------|-----------|
| 1 | `bronze.load()` não era genérico (achado #1 acima) | (a) generalizar com defaults preservando comportamento atual; (b) escrever uma função `load_wide()` paralela | (a) generalizar | Menor superfície nova; mesma técnica já usada em `load_partition()`; zero mudança de comportamento para a dívida, coberta por teste. |
| 2 | Interface do conector: CKAN interno vs. `resource` pré-resolvido (achado #2) | (a) manter `discover()` chamando CKAN internamente; (b) separar `discover_resource()` + `FiscalUniaoConnector(resource=...)` | (b) separar | Replica o padrão já provado do INSS; permite teste de integração via `file://` sem rede, sem precisar mockar CKAN na integração. |
| 3 | Script driver de produção não estava no manifesto do DESIGN | (a) deixar sem ponto de entrada até uma fatia futura; (b) criar `run_fiscal_uniao.py` agora, mesmo padrão de `run_backfill.py` | (b) criar agora | Sem um driver, o pipeline nunca rodaria de verdade contra produção — mesmo padrão de entrega das 2 fatias anteriores (sempre um script manual, nunca wired ao job automático `__main__.py`, que continua exclusivo da dívida). |
| 4 | Rótulo do módulo M02 quando `fiscal_primario` é negativo | (a) mostrar só o valor negativo formatado; (b) mostrar valor + qualificador "(déficit)" | (b) qualificador | Um valor monetário negativo sem contexto pode ler como erro de dado para um usuário leigo do portal público; "(déficit)" é linguagem plana, sem interpretação/recomendação (não viola `ADR-012`/`ADR-049` — é rótulo do sinal aritmético, não uma opinião). |
| 5 | Validação do e2e local antes de deploy | (a) confiar só no build/typecheck; (b) rodar `npm run e2e` localmente contra a API real de produção antes de commitar | (b) rodar contra a API real | Lição da correção do achado ao vivo pós-INSS (PR #14): um e2e nunca executado localmente só falha depois do deploy. Rodar contra a API real (não um preview sem backend) reproduz o cenário de produção fielmente sem precisar deployar o web ainda. |

---

## 5. Blockers / trabalho restante

- **Backfill real não executado** — mecanismo provado só via unit tests + gate `integration` (CI).
  Rodar contra `brasil2036-dev` de verdade é decisão de custo/tempo a confirmar com o usuário,
  mesmo padrão das 2 fatias anteriores.
- **`ckan_package_id`/URL do recurso RTN nunca testados contra a API CKAN real do Tesouro
  Transparente** (só contra uma fixture local e um arquivo baixado manualmente durante o
  `/design`) — o gate `integration`/backfill real vai confirmar se `discover_resource()` funciona
  de verdade contra o endpoint ao vivo.
- **Sem quebra por categoria/função/órgão** — decisão deliberada do DEFINE (C6, total agregado),
  não um gap.
- **Juros (`STORY-009.04`) fora de escopo** — decisão deliberada do Brainstorm, fonte de dado
  distinta (Selic/BCB).

---

## 6. Status transitions

| Arquivo | Status | Próximo |
|---|---|---|
| `DEFINE_FISCAL_RECEITA_DESPESA.md` | ✅ Complete (Built) | `/verify-spec` → `/ship` |
| `DESIGN_FISCAL_RECEITA_DESPESA.md` | ✅ Complete (Built) | idem |

---

## 7. Quality gate

- [x] Todos os itens do manifesto criados/modificados (21 previstos + 2 achados de build: `bronze.py`, `run_fiscal_uniao.py`)
- [x] `ruff` + `mypy --strict` + `pytest` verdes em `ingestion/` (92 testes) e `api/` (20 testes)
- [x] `web/` typecheck + build verdes
- [x] `web/` e2e rodado localmente contra a API real de produção (4/4 passam)
- [x] Sem TODO / sem segredo
- [x] Atribuição de decisões autônomas (§4) — incluindo 1 achado crítico de código (`bronze.load()` não genérico) e 1 refinamento de interface (conector)
- [x] Contratos e configs carregam sem erro
- [x] Achado crítico do `/design` (D10, resultado primário negativo) coberto por teste unitário E de integração (fixture com 1 mês de déficit real)
- [x] Gate `integration` do `ci.yml` — rodou contra BigQuery real no PR #15 (2m37s), provou D10 (mês de déficit real aceito sem quarentena) ao vivo, não só contra `FakeBigQuery`
- [ ] Backfill real — pendente confirmação explícita do usuário
- [x] BUILD_REPORT gerado

---

## 8. Revision history

| Data | Versão | Mudança | Autor |
|---|---|---|---|
| 2026-09-05 | 1.0 | PR1 (espinha de dados) e PR2 (API+web) completos na mesma sessão de build. 2 achados técnicos não previstos pelo DESIGN corrigidos (`bronze.load()` não genérico; interface do conector). Backfill real pendente de confirmação do usuário. `ruff`+`mypy`+`pytest` verdes em `ingestion/` (92 testes) e `api/` (20 testes); `web/` typecheck+build+e2e (4/4, contra API real) verdes. | /build (Claude Sonnet 5) |
| 2026-09-05 | 1.1 | PR1 mergeado (#15) — gate `integration` provou D10 ao vivo contra BigQuery real (mês de déficit real aceito, 2m37s). PR2 pronto para commit/PR. | /build (Claude Sonnet 5) |
