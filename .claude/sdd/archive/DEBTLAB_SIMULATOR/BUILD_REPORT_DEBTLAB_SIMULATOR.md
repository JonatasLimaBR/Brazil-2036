# BUILD REPORT — DEBTLAB_SIMULATOR

## Metadados

- **Feature:** DEBTLAB_SIMULATOR
- **Fase:** 3 (Build)
- **Entrada:** `.claude/sdd/features/DESIGN_DEBTLAB_SIMULATOR.md` (v1.0)
- **Branch:** `feature/debtlab-simulator`
- **Data:** 2026-09-07 a 2026-09-08
- **Status da build:** ✅ Shipped
- **Próximo passo:** — (arquivado)

> Shipped and archived 2026-09-08.

> Nota: assets do plugin SDD ausentes — relatório segue a lista de seções do skill `sdd-build`.

---

## 1. Task execution

### PR1 — Ingestão de PIB real e Dívida Bruta do Governo Geral (BCB SGS)

| # | Arquivo | Ação | Nota |
|---|---|---|---|
| 1 | `ingestion/src/ingestion/connectors/bcb_sgs.py` | Create | `BcbSgsConnector` genérico (1 classe, 2 instâncias — série 4380/13762), suporte a `file://` para testes/integração sem rede |
| 2 | `ingestion/contracts/pib_mensal.yaml` | Create | Contrato do `metric_id=pib_mensal` |
| 3 | `ingestion/contracts/divida_bruta_pib.yaml` | Create | Contrato do `metric_id=divida_bruta_pib` (base real do DebtLab) |
| 4 | `ingestion/sql/silver/pib_mensal.sql` | Create | Silver, `state_ibge_code='BR'` sentinel (convenção de `fiscal_uniao.sql`) |
| 5 | `ingestion/sql/gold/gold_pib_mensal.sql` | Create | Gold, `data_class='observed'` |
| 6 | `ingestion/sql/silver/divida_bruta_pib.sql` | Create | Silver, unidade `pct_pib` (sem conversão, já é % como publicado) |
| 7 | `ingestion/sql/gold/gold_divida_bruta_pib.sql` | Create | Gold — base real que o engine do DebtLab lê, nunca escreve |
| 8 | `ingestion/config/pib_mensal.yaml` | Create | `WideSeriesConfig` YAML, 1 metric_id |
| 9 | `ingestion/config/divida_bruta_pib.yaml` | Create | idem |
| 10 | `ingestion/scripts/run_bcb_macro.py` | Create | Entry point único, parametrizado por `dataset_id` (`pib_mensal`\|`divida_bruta_pib`) |
| 11 | `ingestion/tests/test_bcb_sgs_connector.py` | Create | 9 testes (fetch/parse/validate/checkpoint/file://) |
| 12 | `ingestion/tests/integration/test_pipeline_bcb_macro_bigquery.py` | Create | Integration test real contra `brasil2036-dev` |
| 13 | `ingestion/tests/integration/fixtures/divida_bruta_pib_sample.json` | Create | Fixture com valores reais (81.05/81.93/82.51%, confirmados via API real no `/design`) |

### PR2 — Engine determinístico, Monte Carlo, endpoints, infra

| # | Arquivo | Ação | Nota |
|---|---|---|---|
| 14 | `api/src/api/simulators/__init__.py` | Create | Subpacote novo |
| 15 | `api/src/api/simulators/debtlab.py` | Create | Engine puro: `project_deterministic()`, fórmula de razão dívida/PIB (DESIGN D2) |
| 16 | `api/src/api/simulators/monte_carlo.py` | Create | `run_monte_carlo()`, numpy, P10/P25/P50/P75/P90, seed fixável |
| 17 | `api/pyproject.toml` | Modify | +`numpy>=2.0` |
| 18 | `api/src/api/models.py` | Modify | +`DebtLabScenarioRequest/Response`, `AssumptionDistributionInput`, `YearlyDeterministic`, `YearlyPercentiles`, `DebtLabScenarioBase` — `n_iterations`/`horizon_years` com bounds defensivos (`§2` achado) |
| 19 | `api/src/api/bigquery_repo.py` | Modify | `RunQuery` vira `Protocol` (aceita `maximum_bytes_billed` opcional, achado real, `§2`); `_bq_param_type()` ganha `FLOAT64`/`BOOL`; `debtlab_base()`, `create_debtlab_scenario()`, `get_debtlab_scenario()` |
| 20 | `api/src/api/config.py`/`config.yaml` | Modify | +`bq_dataset_control`, `debtlab_scenarios_table`, `debtlab_base_metric_id`; +`metric_tables` para `pib_mensal`/`divida_bruta_pib` |
| 21 | `api/src/api/main.py` | Modify | +`POST /v1/simulations/debtlab`, `GET /v1/simulations/debtlab/{scenario_id}`; CORS `allow_methods` ganha `POST` |
| 22 | `api/tests/test_debtlab_engine.py` | Create | 5 testes, incluindo 1 cálculo manual completo (AT1) |
| 23 | `api/tests/test_monte_carlo.py` | Create | 5 testes de reprodutibilidade/ordenação de percentis (AT3) |
| 24 | `api/tests/test_debtlab_endpoint.py` | Create | 9 testes de contrato (AT2, AT5, AT6, bounds) |
| 25 | `infra/terraform/cloud_run_services.tf` | Modify | +`google_bigquery_dataset_iam_member.api_control_editor` (`dataEditor` escopado a `br2036_control`); `display_name` atualizado |
| 26 | `docs/adrs/ADR-059-debtlab-engine-and-persistence.md` | Create | Formaliza D1–D5 do DESIGN |
| 27 | `INDEX.md` | Modify | +ADR-059 |
| 28 | `api/openapi/openapi.json` | Modify (regenerado) | Reflete os 2 endpoints novos — `web/src/api-client/schema.d.ts` fica para quando `web/` for tocado de novo (CI só roda `web-check` se `web/` mudar nesse PR) |

---

## 2. Achados técnicos durante o build (não previstos em detalhe pelo DESIGN)

### Achado #1 — 1 conector por série, não 1 pipeline combinado

O manifesto do DESIGN sugeria um único fluxo cobrindo as 2 séries. Investigação real do
`pipeline_wide_series.py` mostrou que ele assume **1 resource = todos os `metric_id`s** (como o
XLSX único do Fiscal, que já vem com 3 métricas). PIB e Dívida/PIB vêm de **2 chamadas HTTP
distintas** (2 séries BCB diferentes) — forçar isso num "1 resource" fabricaria uma URL de
provenance compartilhada errada para uma das 2 métricas, ou arriscaria uma corrida de
`CREATE OR REPLACE` entre 2 execuções sobre a mesma tabela Bronze/Silver/Gold. **Corrigido:** cada
série mantém seu próprio `BcbSgsConnector`, seu próprio Bronze/Silver/Gold table set, sua própria
execução de `pipeline_wide_series.run()` (com `metric_ids=(1,)`) — mesmo princípio de isolamento
já usado entre os 3 datasets INSS. `ADR-059` documenta essa decisão explicitamente (D1).

### Achado #2 — `RunQuery` precisava de um jeito de desligar o cap de bytes por chamada

O DESIGN (D5) já previa `maximum_bytes_billed=None` para o INSERT do cenário, mas a assinatura
existente de `RunQuery` (`Callable[[str, Mapping], list]`) não tinha como carregar esse parâmetro
por chamada — só um valor fixo definido uma vez em `build_bigquery_run_query()`. **Corrigido:**
`RunQuery` virou um `Protocol` com um parâmetro `maximum_bytes_billed` keyword-only e default
(`DEFAULT_MAX_BYTES_BILLED`) — todo call site de 2 argumentos existente continua funcionando sem
mudança (confirmado: as 40 chamadas pré-existentes em `test_bigquery_repo.py`/`test_endpoints.py`
passaram sem alteração).

### Achado #3 — inferência de tipo de parâmetro BigQuery não cobria `float`

`build_bigquery_run_query()` só distinguia `INT64`/`STRING` — qualquer parâmetro `float` (ex.:
`base_divida_pib_pct`) seria enviado como `STRING`, quebrando o `INSERT` (BigQuery rejeitaria a
conversão implícita STRING→FLOAT64 em alguns contextos, ou pior, aceitaria silenciosamente com um
tipo errado). **Corrigido:** `_bq_param_type()` nova, cobre `bool` (checado antes de `int`, já que
`bool` é subclasse de `int` em Python), `int`, `float`, com `STRING` como fallback.

### Achado #4 — risco real de esgotar cota de DML pública sem RBAC

Já antecipado no DESIGN (`§0.6`) como risco aceito, não uma surpresa — mas confirmado aqui como
real, não hipotético: `POST /v1/simulations/debtlab` é o primeiro endpoint de escrita público sem
nenhuma autenticação. Mitigação implementada exatamente como planejado: `n_iterations` (100–20.000)
e `horizon_years` (1–30) validados por `Field(ge=..., le=...)` no Pydantic, retornando `422`
automaticamente fora da faixa (confirmado por teste). Rate-limiting completo continua fora de
escopo (fatia futura de RBAC/ABAC).

### Achado #5 — `RISK-CONTROL-TEST-MATRIX.md` não é o lugar certo para este risco

O manifesto do DESIGN (item 20) previa atualizar esse arquivo para registrar o achado #4. Na
prática, a matriz cobre uma taxonomia fixa de 15 riscos (`R-001`–`R-015`) definida no Discovery
original, cada um ligado a uma capability de IA/agente específica (grounding, approval,
RBAC-por-agente, etc.) — nenhum encaixa precisamente em "endpoint de escrita público sem
rate-limit" sem forçar a categoria. **Decisão:** não modificar esse arquivo (nenhuma das 6 features
anteriores adicionou uma linha nova a ele); o achado fica registrado aqui e no `SHIPPED` como
follow-up rastreado, mesmo padrão usado para outros achados que não se encaixam num artefato fixo
existente.

### Achado #6 (build, não achado de design) — bug no próprio teste de integração

`Decimal('82.51') == 82.51` é `False` em Python (comparação exata `Decimal`↔`float`, não
arredondada) — o teste de integração falhou na primeira execução real contra `brasil2036-dev` por
essa razão, não por um problema no pipeline (o pipeline já tinha `status="ok"`,
`gold_rows=3`, `provenance_rows=3` corretos). Corrigido com `float(latest) ==
pytest.approx(82.51)`; reexecutado com sucesso contra BigQuery real.

### PR3 — Hotfix pós-merge (achado real em produção)

| # | Arquivo | Ação | Nota |
|---|---|---|---|
| 29 | `api/src/api/bigquery_repo.py` | Modify | `maximum_bytes_billed=None` deixa de ser passado literalmente pro `QueryJobConfig` — só entra no kwargs quando não-`None` |
| 30 | `api/tests/test_bigquery_repo.py` | Modify | +1 teste de regressão, verificado que falha contra o padrão com bug e passa contra o fix |

### Achado #7 (pós-merge, achado real em produção, não do build) — `maximum_bytes_billed=None` quebrava o primeiro `INSERT` real

Minutos depois do merge do PR2, o primeiro `POST /v1/simulations/debtlab` real contra
`brasil2036-dev` retornou **500**. Log do Cloud Run mostrou o erro exato do BigQuery: `Invalid
value at 'job.configuration.query.maximum_bytes_billed.value' (TYPE_INT64), "None"`. Causa raiz
confirmada por teste direto: `bigquery.QueryJobConfig(maximum_bytes_billed=None)` serializa o
campo como a **string literal `"None"`** no request (`to_api_repr()` → `{'maximumBytesBilled':
'None'}`), diferente de omitir o kwarg inteiramente (`{}`). `ingestion/bigquery_io.py::run_sql()`
já tinha o padrão certo (só constrói o `job_config` com o campo quando não é `None`); o call site
novo em `api/bigquery_repo.py` (criado nesta própria fatia para o path de escrita) reproduziu o
padrão errado por engano — nenhum call site anterior da API precisava do caso `None`.

**Corrigido** (PR #33, hotfix, squash merge, `ci-gate` verde): kwargs do `QueryJobConfig`
montados condicionalmente. Novo teste de regressão verificado tanto contra o padrão com bug
(assert falha, confirmado manualmente) quanto contra o fix (assert passa) — a asserção precisou
inspecionar `to_api_repr()`, não a propriedade Python (`job_config.maximum_bytes_billed`).

**Correção (achado do `/verify-spec` independente):** a frase original aqui dizia que a
propriedade Python "normaliza pra `None` nos dois casos" — impreciso. Confirmado por teste direto:
`job_config.maximum_bytes_billed` (getter) na verdade **levanta `ValueError` ("invalid literal for
int() with base 10: 'None'")** quando o campo foi setado como `None` explícito, não retorna
silenciosamente `None`. Uma asserção baseada na propriedade também pegaria o bug — só que como uma
exceção confusa no meio do teste, não como uma falha de assert limpa. A escolha de inspecionar
`to_api_repr()` continua correta (é o jeito certo, direto, de verificar o payload real enviado à
API), só a justificativa estava errada.

**Verificado contra produção real após o fix:** `POST /v1/simulations/debtlab` cria e persiste um
cenário real (base = 82,51% real, trajetória de 10 anos calculada corretamente, percentis P10-P90
coerentes); `GET /v1/simulations/debtlab/{scenario_id}` recupera exatamente o mesmo cenário
persistido. Backfill real de produção rodado antes deste teste: `pib_mensal` (438 linhas),
`divida_bruta_pib` (236 linhas) — ambos servindo corretamente via `/v1/metrics/{metric_id}/national`.

---

## 3. Verification results

- **Ingestão:** `ruff check`/`format --check`/`mypy` limpos (24 arquivos fonte, `files =
  ["src/ingestion"]`); `pytest` — 110 passed, 4 deselected (integration).
- **API:** `ruff check`/`format --check`/`mypy` limpos (8 arquivos fonte, `files = ["src/api"]`);
  `pytest` — 41 passed (19 novos: 5 engine + 5 Monte Carlo + 9 endpoint; +1 regressão do hotfix,
  0 regressão nos 21 pré-existentes).
- **Terraform:** `terraform fmt -check` limpo; `terraform validate` (`terraform init
  -backend=false`) — `Success! The configuration is valid.`
- **Integration real contra `brasil2036-dev`:**
  `test_pipeline_bcb_macro_bigquery.py::test_divida_bruta_pib_pipeline_against_bigquery` — **PASS**
  (datasets `citest_<run>_bcbmacro_*` isolados, limpos ao final). Confirma: pipeline real
  RAW→Bronze→Silver→Gold funcionando com a fonte BCB de verdade (via fixture `file://` com valores
  reais), razão dívida/PIB de julho/2026 = 82.51% gravada corretamente em Gold, provenance
  completo (3 linhas), `dataset_registry` atualizado.
- **`api/openapi/openapi.json`** regenerado e commitado — `git diff --exit-code` (mesmo comando do
  gate `lint-typecheck-unit`) confirma que o arquivo commitado bate exatamente com o schema atual
  da API.

---

## 4. Autonomous Decisions

| # | Decision Point | Options Considered | Chose | Rationale |
|---|----------------|--------------------|-------|-----------|
| 1 | 1 conector combinado (DESIGN original) vs. 1 conector por série | (a) forçar as 2 séries num "1 resource" para caber em `pipeline_wide_series.py` como desenhado; (b) 1 execução independente por série, cada uma com seu Bronze/Silver/Gold | (b) | Provenance correta por métrica é inegociável no projeto; forçar (a) fabricaria uma URL de fonte errada para 1 das 2 métricas ou arriscaria colisão de `CREATE OR REPLACE` entre execuções. |
| 2 | `RunQuery` como `Callable` alias vs. `Protocol` | (a) manter `Callable`, adicionar uma função de escrita separada; (b) converter para `Protocol` com parâmetro opcional | (b) | Menos duplicação de lógica de construção de `job_config`; todo call site existente continua válido sem mudança. |
| 3 | Registrar o achado #4 em `RISK-CONTROL-TEST-MATRIX.md` (previsto no DESIGN) | (a) adicionar uma linha `R-016` nova; (b) não modificar, documentar como follow-up no BUILD_REPORT/SHIPPED | (b) | A matriz é uma taxonomia fixa de 15 riscos de IA/agente do Discovery original; nenhuma das 6 features anteriores adicionou uma linha nova a ela mesmo introduzindo achados novos — manter o precedente. |
| 4 | `web/src/api-client/schema.d.ts` — regenerar nesta PR ou não | (a) regenerar proativamente; (b) deixar para quando `web/` for tocado de novo | (a), corrigido | Decisão original (b) partiu de uma suposição errada — `web-check` na verdade roda sempre que `api/openapi/openapi.json` muda, não só quando `web/` muda; o CI do PR2 pegou a divergência real (`git diff --exit-code -- src/api-client/schema.d.ts` falhou). Corrigido no mesmo PR: `npm run gen:client` rodado de verdade, `typecheck`/`build` conferidos localmente antes de re-enviar. |

---

## 5. Blockers / trabalho restante

Nenhum blocker. Backfill real contra `brasil2036-dev` (fora do dataset `citest_*` isolado do
teste de integração) já executado: `pib_mensal` (438 linhas), `divida_bruta_pib` (236 linhas) —
ambos servindo corretamente em produção. Endpoint de simulação (`POST`/`GET
/v1/simulations/debtlab`) verificado ao vivo, ponta a ponta, após o hotfix do Achado #7.

---

## 6. Status transitions

| Arquivo | Status | Próximo |
|---|---|---|
| `DEFINE_DEBTLAB_SIMULATOR.md` | ✅ Complete (Built) | `/verify-spec` → `/ship` |
| `DESIGN_DEBTLAB_SIMULATOR.md` | ✅ Complete (Built) | idem |

---

## 7. Revision history

| Data | Versão | Mudança | Autor |
|---|---|---|---|
| 2026-09-07 | 1.0 | Build completo: PR1 (ingestão BCB SGS real, PIB + Dívida Bruta do Governo Geral) + PR2 (engine determinístico, Monte Carlo, endpoints, IAM Terraform, ADR-059). 6 achados reais durante o build (2 de arquitetura de pipeline, 2 de tipagem de query, 1 de escopo de risco, 1 bug no próprio teste). Integration test real contra `brasil2036-dev` PASS. `typecheck`/`lint`/`unit` verdes em ambos os pacotes, 0 regressão. | /build (Claude Sonnet 5) |
| 2026-09-08 | 1.1 | PR3 (hotfix pós-merge): achado real #7 em produção — `maximum_bytes_billed=None` quebrava o primeiro `INSERT` real (`BadRequest` do BigQuery). Corrigido, teste de regressão verificado contra o padrão com bug e contra o fix. Backfill real de produção executado (`pib_mensal` 438 linhas, `divida_bruta_pib` 236 linhas). `POST`/`GET /v1/simulations/debtlab` verificados ao vivo, ponta a ponta, contra produção real. Status → pronto para `/verify-spec`. | /build (Claude Sonnet 5) |
