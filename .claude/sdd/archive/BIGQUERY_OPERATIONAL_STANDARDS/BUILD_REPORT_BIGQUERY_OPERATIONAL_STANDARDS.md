# BUILD REPORT — BIGQUERY_OPERATIONAL_STANDARDS

## Metadados

- **Feature:** BIGQUERY_OPERATIONAL_STANDARDS
- **Fase:** 3 (Build)
- **Entrada:** `.claude/sdd/features/DESIGN_BIGQUERY_OPERATIONAL_STANDARDS.md` (v1.0)
- **Branch:** `chore/bigquery-operational-standards`
- **Data:** 2026-09-06
- **Status da build:** ✅ Shipped. `/verify-spec` independente = OVERALL PASS (~92%), 1 achado WARNING corrigido (§4b).
- **Próximo passo:** nenhum — feature arquivada. Próxima feature via `/brainstorm` ou `/define`.

> Assets do plugin SDD ausentes — relatório segue a lista de seções do skill `sdd-build`.

---

## 1. Task execution

| # | Arquivo | Ação | Nota |
|---|---|---|---|
| 1 | `docs/specs/SPEC-034-BIGQUERY-OPERATIONAL-STANDARDS.md` | Create | Cap de custo + particionamento/clustering + retenção |
| 2 | `docs/adrs/ADR-057-bigquery-cost-guardrail.md` | Create | Formaliza D1-D3 do DESIGN |
| 3 | `ingestion/src/ingestion/bigquery_io.py` | Modify | `DEFAULT_MAX_BYTES_BILLED`, `run_sql()`/`scalar()` ganham `maximum_bytes_billed`, `BigQueryClient.query()` ganha `job_config` |
| 4 | `ingestion/tests/_fakes.py` | Modify | `FakeBigQuery.query()` aceita e registra `job_config` |
| 5 | `ingestion/tests/test_bigquery_io.py` | Create | 5 testes: default aplica cap, `None` desliga, valor customizado, `scalar()` idem |
| 6 | `ingestion/src/ingestion/bronze.py` | Modify | Toda chamada `run_sql`/`scalar` em `load()`/`load_partition()` passa `maximum_bytes_billed=None` |
| 7 | `ingestion/tests/test_bronze_partition.py` | Modify | +2 testes de regressão: `load()`/`load_partition()` sem cap algum |
| 8 | `api/src/api/bigquery_repo.py` | Modify | `build_bigquery_run_query()`: `QueryJobConfig` ganha `maximum_bytes_billed` |
| 9 | `api/tests/test_bigquery_repo.py` | Modify | +1 teste (mock real de `bigquery.Client`) confirmando o cap no `job_config` construído |
| 10 | `docs/risks/RISK-CONTROL-TEST-MATRIX.md` | Modify | `R-012` distingue "cap por query: implementado" de "orçamento de projeto: não implementado" |
| 11 | `INDEX.md` | Modify | +SPEC-034, +ADR-057 |

Todos os 11 itens do manifesto do DESIGN foram criados/modificados exatamente como planejado —
nenhum achado técnico de build fora do previsto (diferente das 3 fatias anteriores, que sempre
encontraram pelo menos 1 achado real durante a implementação). A investigação de comportamento
real do BigQuery (LOAD DATA é carga grátis, tabelas clusterizadas têm estimativa *upper bound*)
já tinha sido feita na Fase 2 (`/design §0`), então o build não teve descoberta nova — só executou
o que já estava desenhado com evidência real.

---

## 2. Verification results

- `ruff check .` (ingestion + api) — PASS
- `ruff format --check .` (ingestion + api) — PASS
- `mypy src` (strict, ingestion + api) — PASS, 23 + 5 arquivos-fonte, 0 erros
- `pytest -q -m "not integration"` (ingestion) — **99 passed** (92 → 99, +7 novos), 3 deselected (integration)
- `pytest -q` (api) — **21 passed** (20 → 21, +1 novo)

Não há gate `integration` novo a rodar de verdade nesta fatia (nenhum dataset/tabela novo é
criado) — o gate `integration` já existente do `ci.yml` roda os 3 pipelines reais (dívida, INSS,
fiscal) contra BigQuery de produção-isolada a cada PR, e serve como a prova viva de que o cap não
quebra nenhuma query real do projeto (S2/AT3 do DEFINE).

---

## 3. Autonomous Decisions

| # | Decision Point | Options Considered | Chose | Rationale |
|---|----------------|--------------------|-------|-----------|
| 1 | Onde exatamente aplicar `maximum_bytes_billed=None` dentro de `bronze.py` — só na chamada `LOAD DATA`, ou em toda a função? | (a) só a chamada `LOAD DATA`; (b) toda chamada `run_sql`/`scalar` dentro de `load()`/`load_partition()` | (b) toda a função | Já decidido no DESIGN (D3) com o racional completo — deixar o cap ativo só em parte do fluxo de uma carga potencialmente grande (ex.: o `CREATE OR REPLACE ... FROM staging` ou o `COUNT(*)` de confirmação) seria pior que não ter cap algum: a carga passaria, e uma etapa seguinte sobre a mesma tabela grande falharia de forma confusa. |
| 2 | Como testar `build_bigquery_run_query()` (constrói um `bigquery.Client` real internamente, não injetável) | (a) refatorar para injeção de dependência; (b) mockar `google.cloud.bigquery.Client` via `unittest.mock.patch` | (b) mock | Menor mudança de superfície — a função já é testada indiretamente via `BigQueryRepo` com um `run_query` fake; só o cap em si precisa de um teste que veja o `job_config` real construído, e `patch` resolve isso sem mudar a assinatura pública da função. |

---

## 3b. Achado real não planejado: bug em `verify_chain.py` (corrigido, PR #21)

O merge do PR desta feature (#20) disparou o job automático `data.yml` (roda o pipeline da
dívida em produção a cada push que toca `ingestion/**`). O passo final, "verify provenance
chain" (`ingestion/scripts/verify_chain.py`), **falhou de verdade**: `provenance coverage 63 !=
gold rows 27`.

**Não é um bug desta feature** — é um bug pré-existente no script, exposto agora porque
`metric_provenance` é compartilhada (`ADR-055`) e o backfill real da fatia `FISCAL_RECEITA_DESPESA`
(1997–2026) tem linhas no mesmo `reference_year` da dívida (2022): a query do script contava
`COUNT(*)` em `metric_provenance` filtrando só por `reference_year`, sem filtrar `metric_id` —
somava 27 linhas da dívida + 36 linhas fiscais (12 meses × 3 métricas) = 63.

Corrigido com um filtro `--metric-id` explícito (default `divida_consolidada`, mantendo o uso
atual). Verificado contra `brasil2036-dev` real antes e depois da correção (query manual
reproduziu o 63 exato do CI; a versão corrigida retornou 27; o script rodado de ponta a ponta
contra produção imprimiu `OK reference_year=2022 entities=27 provenance_rows=27`). Mergeado
como PR #21, e o `data.yml` seguinte confirmou o passo verde em produção real.

Sem teste automatizado dedicado (mesmo padrão de `run_backfill.py`/`run_fiscal_uniao.py` —
scripts em `ingestion/scripts/` não têm cobertura de teste unitário neste projeto; a verificação
foi por execução real contra produção, documentada acima).

---

## 4. Blockers / trabalho restante

Nenhum. Todos os MUST (G1-G8) e o SHOULD (G9, retenção documentada no `SPEC-034 §3`) do DEFINE
foram entregues. G10 (COULD — nota no `CLAUDE.md` apontando o SPEC) será feito no `/ship`, junto
da sincronização padrão de `CLAUDE.md`.

---

## 4b. `/verify-spec` independente (2026-09-06)

Sessão nova, read-only, sem contexto do build. Inspecionou o código real, rodou `ruff`/`mypy`/
`pytest` de verdade, grepeou todo `run_sql`/`scalar` call site de `ingestion/` para confirmar
cobertura de 100% (AT1), comparou o `SPEC-034` contra as 10 SQL reais existentes (AT5), e
consultou `brasil2036-dev` para reproduzir de forma independente o bug/correção do
`verify_chain.py` (`§3b`).

**Veredito: OVERALL PASS — confiança ~92%.**

- AT1, AT2, AT3, AT5 (com ressalva), AT6, AT7, AT8 e S1, S2, S4, S5, S6, S7 = PASS, com evidência
  concreta (grep real, query real contra BigQuery, `gh pr view` confirmando `ci-gate: SUCCESS`
  nos PRs #20 e #21).
- Reproduziu de forma independente o achado do `§3b`: consultou `metric_provenance` real e
  confirmou `27 (dívida) + 12+12+12 (fiscal) = 63`, exatamente o número da falha real; rodou
  `verify_chain.py` corrigido contra produção e confirmou `OK ... provenance_rows=27`.
- **1 achado WARNING real (AT4/S3): o DESIGN prometia um teste provando a falha acima do cap
  ("AT4 usa um cap artificialmente baixo... para provar a falha"), mas `test_bigquery_io.py`
  original só testava que o valor do cap chegava ao `job_config` — nunca que excedê-lo realmente
  falha.** Corrigido nesta rodada: `_RejectingFakeBigQuery` (fake que modela o comportamento real
  do BigQuery — rejeita antes de executar quando o tamanho estimado excede o cap) +
  `test_run_sql_propagates_bigquery_rejection_above_the_cap` /
  `test_scalar_propagates_bigquery_rejection_above_the_cap`, confirmando que a exceção
  (`google.api_core.exceptions.BadRequest`) propaga sem ser engolida ou mascarada.
- **1 achado INFO (cosmético): `SPEC-034 §2`** dizia que todo `gold_inss_beneficios_*` clusteriza
  por `especie_codigo`, mas `gold_inss_beneficios_mantidos` na verdade clusteriza por
  `status_manutencao`. Corrigido — o texto agora nomeia cada tabela individualmente e explicita
  que o campo de clustering é a chave de negócio mais usada *daquela* tabela, não
  necessariamente igual entre tabelas do mesmo domínio.
- Nenhum achado CRITICAL ou ERROR. Nenhuma regra inegociável do `CLAUDE.md` violada.

---

## 5. Status transitions

| Arquivo | Status | Próximo |
|---|---|---|
| `DEFINE_BIGQUERY_OPERATIONAL_STANDARDS.md` | ✅ Complete (Built) | `/verify-spec` → `/ship` |
| `DESIGN_BIGQUERY_OPERATIONAL_STANDARDS.md` | ✅ Complete (Built) | idem |

---

## 6. Quality gate

- [x] Todos os itens do manifesto criados/modificados (11 de 11)
- [x] `ruff` + `mypy --strict` + `pytest` verdes em `ingestion/` (101 testes, +2 do achado do `/verify-spec`) e `api/` (21 testes)
- [x] Sem TODO / sem segredo
- [x] Atribuição de decisões autônomas (§3)
- [x] `SPEC-034`/`ADR-057` refletem a convenção real já em uso, não uma regra inventada (C3 do DEFINE)
- [x] `RISK-CONTROL-TEST-MATRIX.md` atualizado sem inflar cobertura (`R-012` distingue implementado de não implementado)
- [x] Mudança de código 100% aditiva (C1) — nenhum caller existente das 3 fatias mudou de comportamento, confirmado pelas 99+21 suites verdes
- [x] BUILD_REPORT gerado

---

## 7. Revision history

| Data | Versão | Mudança | Autor |
|---|---|---|---|
| 2026-09-06 | 1.0 | Build completo em 1 PR (sem dependência entre pacotes). 11 de 11 itens do manifesto entregues sem achado técnico novo (investigação real já feita na Fase 2). `ruff`+`mypy`+`pytest` verdes em `ingestion/` (99 testes, +7) e `api/` (21 testes, +1). Status → Ready for `/verify-spec`. | /build (Claude Sonnet 5) |
| 2026-09-06 | 1.1 | Achado real não planejado: bug pré-existente em `verify_chain.py` exposto pelo backfill fiscal real, corrigido e verificado contra produção (`§3b`, PR #21). `/verify-spec` independente = OVERALL PASS (~92%); achado WARNING (AT4/S3 não exercitado de verdade) corrigido com `_RejectingFakeBigQuery` + 2 testes novos; achado INFO cosmético em `SPEC-034 §2` corrigido. `ingestion/` 101 testes. Pronto para `/ship`. | /build (Claude Sonnet 5) |
