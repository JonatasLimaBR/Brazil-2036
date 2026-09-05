# BUILD REPORT — INSS_BENEFICIOS

## Metadados

- **Feature:** INSS_BENEFICIOS
- **Fase:** 3 (Build)
- **Entrada:** `.claude/sdd/features/DESIGN_INSS_BENEFICIOS.md` (v1.0)
- **Branch:** PR1 `feature/inss-beneficios` (merged) · PR2 `feature/inss-beneficios-pr2` (merged)
- **Data:** 2026-09-04 a 2026-09-05
- **Status da build:** 🔶 **PR1+PR2 completos e mergeados. Backfill real: Indeferidos completo (37/38 meses); Emitidos e Mantidos ainda não iniciados.**
- **Próximo passo:** backfill real de Emitidos e Mantidos (medir tempo/custo, começando por `--limit` pequeno) → `/verify-spec` → `/ship`.

> Assets do plugin SDD ausentes — relatório segue a lista de seções do skill `sdd-build`.

---

## 1. Task execution (PR1 — espinha de dados)

| # | Arquivo | Ação | Agente | Nota |
|---|---|---|---|---|
| 1 | `docs/adrs/ADR-055-inss-incremental-partitioned-ingestion.md` | Create | `architect`→`(direct)` | Formaliza backfill resumível + escrita por partição, e a correção crítica de `registry.py`/`provenance.py` (achado #1 abaixo) |
| 2 | `ingestion/src/ingestion/ckan.py` | Create | `python-developer`→`(direct)` | Lister CKAN genérico |
| 3 | `ingestion/tests/test_ckan.py` | Create | `python-reviewer`→`(direct)` | 2 testes |
| 4 | `ingestion/reference/uf_ibge.csv` | Modify | `python-developer`→`(direct)` | +coluna `state_name_normalized` (gerada por script, não digitada à mão) |
| 5 | `ingestion/src/ingestion/connectors/inss_emitidos.py` | Create | `ai-data-engineer-gcp`→`(direct)` | Conector real, schema confirmado contra arquivo real (não suposição) |
| 6 | `ingestion/src/ingestion/connectors/inss_mantidos.py` | Create | `ai-data-engineer-gcp`→`(direct)` | Idem; normaliza o quirk de delimitador header-vírgula/dados-ponto-e-vírgula, confirmado real |
| 7 | `ingestion/src/ingestion/connectors/inss_indeferidos.py` | Create | `ai-data-engineer-gcp`→`(direct)` | XLSX→CSV, schema real de 2 linhas de cabeçalho confirmado |
| 8 | `ingestion/tests/test_inss_connectors.py` | Create | `python-reviewer`→`(direct)` | 7 testes (download, validate, checkpoint, formatos) |
| 9 | `ingestion/src/ingestion/bronze.py` | Modify | `python-developer`→`(direct)` | +`load_partition()`, escopado por `(reference_period, source_uri)` — achado #3 |
| 10 | `ingestion/tests/test_bronze_partition.py` | Create | `python-reviewer`→`(direct)` | 3 testes, incluindo o caso de 2 recursos no mesmo mês |
| 11 | `ingestion/src/ingestion/pipeline_incremental.py` | Create *(desvio do §5.2 do DESIGN — achado #2)* | `python-developer`→`(direct)` | Novo módulo, não modifica `pipeline.run()` |
| 12 | `ingestion/tests/test_pipeline_incremental.py` | Create | `python-reviewer`→`(direct)` | 4 testes, incluindo acumulação entre 2 períodos |
| 13 | `ingestion/src/ingestion/backfill.py` | Create | `python-developer`→`(direct)` | Orquestrador resumível; chama `ensure_uf_ibge` 1x por backfill, não por recurso |
| 14 | `ingestion/tests/test_backfill.py` | Create | `python-reviewer`→`(direct)` | 4 testes |
| 15 | `ingestion/src/ingestion/registry.py` | Modify *(achado #1 — CRÍTICO)* | `python-developer`→`(direct)` | `CREATE OR REPLACE` → `MERGE` escopado por `dataset_id` |
| 16 | `ingestion/src/ingestion/provenance.py` | Modify *(achado #1 — CRÍTICO)* | `python-developer`→`(direct)` | `CREATE OR REPLACE` → `DELETE+INSERT` escopado por `(metric_id, reference_date)`; `reference_year` → `reference_date` |
| 17 | `ingestion/src/ingestion/pipeline.py` | Modify | `python-developer`→`(direct)` | 1 ponto de chamada atualizado para a nova assinatura de `provenance.write_from_gold` |
| 18 | `ingestion/src/ingestion/contract.py` | Modify | `python-developer`→`(direct)` | +`check_gold_period()` — sem contagem fixa de entidades (grão multi-dimensão não tem cardinalidade única por período) |
| 19 | `ingestion/tests/test_registry.py`, `test_provenance.py` | Modify | `python-reviewer`→`(direct)` | Reescritos para o comportamento correto (os antigos afirmavam o bug como comportamento esperado) |
| 20 | `ingestion/contracts/inss_beneficios_{emitidos,mantidos,indeferidos}.yaml` | Create | `data-contracts-engineer`→`(direct)` | Schema real confirmado; nota de privacidade explícita (`never_expose: cid10, dt_nascimento*`) |
| 21 | `ingestion/sql/silver/inss_beneficios_{emitidos,mantidos,indeferidos}.sql` | Create | `sql-optimizer`→`(direct)` | DELETE+INSERT por partição; UF casada por nome sem acento (NFD); filtro `WHERE b._reference_period = ...` — achado #4 |
| 22 | `ingestion/sql/gold/gold_inss_beneficios_{emitidos,mantidos,indeferidos}.sql` | Create | `sql-optimizer`→`(direct)` | Agregação GROUP BY; Indeferidos usa `COUNT` (sem campo monetário na fonte) |
| 23 | `ingestion/config/inss_{emitidos,mantidos,indeferidos}.yaml` | Create | `(direct)` | 1 config por dataset |
| 24 | `ingestion/pyproject.toml` | Modify | `(direct)` | +`openpyxl`, +`types-openpyxl` |
| 25 | `ingestion/tests/integration/fixtures/inss_emitidos_sample.csv` + contrato de fixture | Create | `data-quality-analyst`→`(direct)` | Só Emitidos (DESIGN §6: maior risco de formato/volume) |
| 26 | `ingestion/tests/integration/test_pipeline_inss_bigquery.py` | Create | `data-quality-analyst`→`(direct)` | `@pytest.mark.integration`; não executado nesta sessão (sem `GCP_PROJECT`) |
| 27 | `infra/terraform/cloud_run.tf` | Modify | `ci-cd-specialist`→`(direct)` | 512Mi/900s → 4Gi/3600s (dimensionado para o maior arquivo real conhecido, 1,2 GB) |
| 28 | `backlog/BACKLOG-MESTRE.md` | **Não modificado** *(achado #5)* | — | `STORY-010.03` (e 010.04/05/06) já existiam — a suposição do DEFINE (G11) veio de um grep truncado |
| 29 | `INDEX.md` | Modify | `(direct)` | +ADR-055 |

Delegação via Task tool: nenhuma (agentes casados não têm ferramenta de escrita nesta sessão; execução direta a partir dos padrões §5 do DESIGN, ajustados pelos achados abaixo).

## 1b. Task execution (PR2 — API + web)

| # | Arquivo | Ação | Agente | Nota |
|---|---|---|---|---|
| 30 | `api/src/api/bigquery_repo.py` | Modify | `python-developer`→`(direct)` | +`latest_national_total(metric_id, gold_table)` — desvio de escopo do R10/OQ1 (achado #10) |
| 31 | `api/src/api/models.py` | Modify | `python-developer`→`(direct)` | +`NationalMetricResponse` |
| 32 | `api/src/api/main.py` | Modify | `python-developer`→`(direct)` | +rota nova `GET /v1/metrics/{metric_id}/national` — aditiva, não toca `/v1/metrics/{metric_id}` da dívida |
| 33 | `api/src/api/config.py`, `config.yaml` | Modify *(não previsto no manifesto original)* | `python-developer`→`(direct)` | +`metric_tables: dict[metric_id, gold_table]` — resolve qual Gold físico por `metric_id` |
| 34 | `api/tests/test_bigquery_repo.py`, `test_endpoints.py` | Modify | `python-reviewer`→`(direct)` | +6 testes; 1 prova explicitamente que a rota da dívida não regride (C9) |
| 35 | `api/openapi/openapi.json` | Modify | `(direct)` | Regenerado via `scripts/export_openapi.py` |
| 36 | `web/src/inss.ts` | Create | `typescript-reviewer`→`(direct)` | Módulo M03, 1 fetch por metric_id, renderiza valor + `data_class` + link fonte, ou "Indisponível" |
| 37 | `web/index.html`, `styles.css`, `main.ts` | Modify | `typescript-reviewer`→`(direct)` | Seção `#inss-module` + grid de 3 números |
| 38 | `web/src/api-client/schema.d.ts` | Modify | `(direct)` | Regenerado via `npm run gen:client` |
| 39 | `web/tests/e2e/card.spec.ts` | Modify | `python-reviewer`→`(direct)` | +teste smoke da renderização dos 3 números (achado #11 — não afirma valor real, dado que o backfill ainda não rodou) |

### Resolução de OQ1/OQ2 (DEFINE, ainda abertas no DESIGN)
- **OQ1** (generalizar `BigQueryRepo` vs. rota dedicada): resolvida como **rota nova + agregação nacional**, mais simples que o "grão mês+espécie completo" que o R10 original previa — ver achado #10.
- **OQ2** (total nacional vs. UF-piloto): resolvida como **total nacional** (soma de todas as UF e espécies do mês mais recente), consistente com a decisão do Brainstorm ("1 módulo com os 3 números", não um por UF).

---

## 2. Descoberta real durante o Build (além da já registrada no DESIGN §0)

A descoberta do DESIGN já havia revelado volume/formato reais. Durante o **Build**, a implementação
efetiva revelou **schemas de coluna reais** (não assumidos) para os 3 datasets:

- **Emitidos:** 14 colunas confirmadas via `curl`+`unzip -p` num arquivo real (`despacho;
  sexo_recebedor;clientela;tipo_beneficio;uf;meio_pagamento;banco;municipio;municipio_resid;
  vl_liquido;ramo_atividade;Dt_Inicio_Validade;especie;especie_codigo_nome`).
- **Mantidos:** 17 colunas confirmadas via range-request numa CSV real de "Suspensos" — e um quirk
  real descoberto: o **cabeçalho vem delimitado por vírgula, mas as linhas de dado vêm por
  ponto-e-vírgula**. Inclui `cid10` (código de diagnóstico) e `dt_nascimento_titular` — mais
  sensível do que assumido no Brainstorm/DEFINE.
- **Indeferidos:** 14 colunas confirmadas baixando e abrindo o XLSX real com `openpyxl` — a planilha
  tem uma **linha de título antes do cabeçalho real** (linha 0 = título, linha 1 = cabeçalho, dados
  a partir da linha 2), e repete o texto "Espécie"/"APS" para pares código/nome adjacentes.

Nenhum desses 3 schemas foi inventado — todos vieram de inspeção real de arquivo, seguindo a
mesma disciplina do MVP_WALKING_SKELETON.

---

## 3. Verification results

| Check | Comando | Resultado |
|---|---|---|
| `ingestion/` lint+format | `uv run ruff check .` + `ruff format --check .` | ✅ |
| `ingestion/` types (strict) | `uv run mypy` | ✅ (21 arquivos) |
| `ingestion/` unit | `uv run pytest -q` (marker `not integration`) | ✅ **64 passed**, 2 deselected (debt + INSS `integration`, ambos pulados sem `GCP_PROJECT`) |
| Contratos carregam | `DataContract.load()` nos 3 YAML novos | ✅ |
| Configs carregam | `load_incremental_config()` nos 3 YAML novos | ✅ |
| `terraform fmt` | `terraform fmt -check -diff` em `cloud_run.tf` | ✅ |
| `integration` (BigQuery real) | PR #4, `ci.yml` `integration` job | ✅ **PASS ao vivo** — `status=ok`, 5 linhas Bronze/Gold/provenance, lineage fecha (`file://` → `gs://` → registry). 1ª tentativa pegou um bug real na asserção do teste (grão UF×espécie, não só UF — 5 linhas, não 3); corrigido e reexecutado, verde. |
| `api/` lint+format | `ruff check .` + `ruff format --check .` | ✅ |
| `api/` types (strict) | `uv run mypy` | ✅ (5 arquivos) |
| `api/` unit | `uv run pytest -q` | ✅ **15 passed** (9 existentes da dívida + 6 novas de INSS) |
| `web/` types | `npm run typecheck` | ✅ |
| `web/` build | `npm run build` | ✅ 8,75 kB (gzip 3,33 kB) — sem valor numérico hard-coded |
| `web/` e2e | `npm run e2e` | ⚠️ **não executado** — precisa de um servidor `preview` + API viva; roda no `api-web.yml` pós-deploy (mesmo padrão do card da dívida) |
| Backfill real (183 recursos, ~100–130 GB) | — | ⚠️ **não executado** — operação longa/custosa; deliberadamente não disparada sem confirmação explícita do usuário (ver Blockers) |

---

## 4. Autonomous Decisions

| # | Achado / Decisão | Opções | Escolha | Racional |
|---|---|---|---|---|
| 1 | **CRÍTICO** — `registry.upsert_dataset_registry()` e `provenance.write_from_gold()` faziam `CREATE OR REPLACE TABLE` em tabelas **compartilhadas** (`dataset_registry`, `metric_provenance`). Rodar para INSS apagaria a linha/os dados da dívida já em produção. Os testes antigos (`test_upsert_dataset_registry_uses_create_or_replace_no_dml`) afirmavam esse comportamento como correto. | (a) Ignorar, já que "funcionava" para 1 dataset; (b) corrigir para `MERGE`/`DELETE+INSERT` escopado | (b) | Achado durante a leitura do código antes de escrever o 1º conector — corrigir agora é mais barato que descobrir isso rodando contra produção. Formalizado em ADR-055. Testes antigos reescritos para o comportamento correto (não deletados). |
| 2 | `pipeline.run()` (dívida) vs. estender para múltiplos recursos | (a) mudar a assinatura de `pipeline.run()` conforme o esboço §5.2 do DESIGN; (b) novo módulo `pipeline_incremental.py`, `pipeline.run()` intocado | (b) | Zero risco à função já testada/em produção da fatia #1; desvio pontual do esboço exato do DESIGN, mas realiza a mesma decisão D1/D3. |
| 3 | Escopo do `DELETE` em `bronze.load_partition()`: só `reference_period` (como no §5.3 do DESIGN) apagaria as linhas de um sub-recurso ao carregar outro do mesmo mês — Mantidos publica 3 recursos/mês (Ativos/Suspensos/Cessados) | (a) manter escopo só por período; (b) escopar por `(reference_period, source_uri)` | (b) | Achado ao raciocinar sobre o fluxo de Mantidos antes de escrever o SQL — sem isso, carregar "Suspensos" apagaria as linhas de "Ativos" do mesmo mês. |
| 4 | SQL de Silver sem filtro de período no `SELECT ... FROM bronze` — cada run reprocessaria **todo** o histórico acumulado de Bronze, não só o mês corrente | (a) manter como no esboço; (b) adicionar `WHERE b._reference_period = ...` | (b) | Bug real pego escrevendo o teste `test_incremental_pipeline_two_periods_accumulate_not_overwrite` — sem o filtro, a 2ª chamada reinseriria duplicatas do 1º período. |
| 5 | `STORY-010.03` (indeferidos) — o DEFINE (G11) assumia que faltava no backlog, baseado num `grep -A 2` truncado | (a) adicionar de qualquer forma; (b) verificar antes | (b) | Já existia (linha 106), junto com 010.04/05/06 — evitada uma entrada duplicada. |
| 6 | `check_gold()` existente (dívida) assume contagem fixa de entidades (`= 27`) — não se aplica ao grão multi-dimensão do INSS (UF×espécie[×status]×mês não tem cardinalidade única por período) | (a) forçar INSS pelo `check_gold()` existente com um `expected_entity_count` fabricado; (b) `check_gold_period()` novo, sem essa asserção | (b) | (a) exigiria inventar um número sem base real, violando "nunca fabricar métrica" em espírito; (b) mantém as checagens que fazem sentido universalmente (NOT NULL, não-negativo, cobertura de provenance). |
| 7 | Indeferidos não tem campo monetário na fonte real (só contagem de indeferimentos) | (a) forçar um `value` fictício; (b) `value = COUNT(*)`, `unit = 'count'` | (b) | Reflete o dado real; documentado no contrato (`allowed: [count]`). |
| 8 | `bronze_check` da pipeline incremental comparava `config.bronze_columns` contra `contract.source_columns` — ambos estáticos, checagem circular (nunca pegaria drift real) | (a) manter; (b) reusar `bronze.source_columns()` (já existente, consulta `INFORMATION_SCHEMA.COLUMNS` real) | (b) | (a) nunca detectaria uma mudança real de schema na fonte; (b) reaproveita função já testada, sem código novo. |
| 9 | Memória/timeout do Cloud Run Job (512Mi/900s) insuficientes para o maior arquivo real conhecido (1,2 GB comprimido, Mantidos Ativos) | (a) manter; (b) 4Gi/3600s | (b) | Dimensionado para 1 recurso confortavelmente; nota explícita de que o backfill completo (183 recursos numa execução só) provavelmente precisa de mais — a medir no primeiro run real. |
| 10 | R10/OQ1 do DEFINE pedia "grão mês+espécie completo" na API — mas o módulo M03 (decisão do Brainstorm) só precisa de **1 número nacional por dataset** para o mês mais recente | (a) implementar o endpoint genérico UF×espécie×mês completo, mais superfície e complexidade; (b) endpoint de total nacional agregado (`SUM` de tudo), mais simples | (b) | YAGNI — a UI real só consome 1 agregado por dataset; drill-down por UF/espécie não tem consumidor ainda. `Config.metric_tables` deixa o caminho aberto para estender depois sem quebrar nada. |
| 11 | Teste e2e do módulo M03: afirmar um valor real renderizado (como o card da dívida faz) exigiria dado real no Gold, que só existe após o backfill (ainda não rodado) | (a) afirmar um valor específico (falharia até o backfill rodar); (b) teste smoke — renderiza valor OU "Indisponível" com grace, nunca quebra | (b) | Honesto sobre o estado real dos dados; evita um teste que falharia por design até o backfill rodar. Vira teste de valor estrito depois, quando houver dado real. |
| 12 | Achado #10 exigiu saber, por `metric_id`, qual tabela Gold física consultar — `Config` da API não tinha esse conceito (só 1 `gold_table` fixo, para a dívida) | (a) hardcode do nome da tabela INSS no código; (b) `metric_tables: dict[str,str]` novo em `Config`/`config.yaml` | (b) | Generaliza para qualquer metric_id futuro sem tocar código, só o YAML; mantém `gold_table`/`default_metric_id` da dívida intocados (C9). |

---

## 4b. Backfill real — Indeferidos (2026-09-05)

Executado contra `brasil2036-dev` real, com confirmação explícita do usuário em 2 etapas: (1)
`--limit 1` para provar o mecanismo, (2) histórico completo depois de verificado.

### Achados novos, só visíveis rodando contra o CKAN real de verdade

| # | Achado | Correção |
|---|---|---|
| 13 | **Bug crítico de path**: `_REPO_INGESTION_ROOT` em `pipeline_incremental.py` apontava 1 nível acima do correto (`ingestion/src` em vez de `ingestion/`) — `config.contract_path` nunca resolvia de verdade; nenhum teste unitário pegou isso porque nenhum verificava `contract_path.exists()` contra o layout real do repo (só contra `tmp_path` sintético). Só apareceu rodando de verdade. Corrigido; teste de regressão novo (`test_pipeline_incremental_config.py`) verifica os 3 configs reais. | Fix + teste |
| 14 | **Nomes de arquivo de Indeferidos não têm padrão YYYYMM nenhum** (confirmado: 38/38 arquivos reais usam nome de mês em português, formatos inconsistentes, às vezes MMYYYY invertido) — `parse_period_from_url` (usado para Emitidos/Mantidos) não serve para este dataset. Resolvido com `period_resolver` novo e injetável em `run_backfill()`: para Indeferidos, baixa o arquivo e lê o período direto da própria coluna `competencia_indeferimento` (dado se autodescreve, mesmo espírito do D5). | `backfill.PeriodResolver` + resolver dedicado em `scripts/run_backfill.py` |
| 15 | `limit` resolvia o período (caro para Indeferidos — baixa o arquivo inteiro) para **todos** os recursos antes de aplicar o limite, não só para os que seriam processados — 38 downloads em vez de 1 no teste `--limit 1`. | Reordenado: checa `limit` antes de chamar `period_resolver`; `break` implícito via `continue` no início do loop |
| 16 | **1 arquivo real (Junho/2024) tem layout de coluna diferente dos outros 37** — `competencia_indeferimento` não está na primeira coluna nesse arquivo específico (nome de arquivo também foge do padrão: sem ano, "INDEFERIDOS+JUNHO+_DADOS+ABERTOS.xlsx"). O resolver corretamente **rejeitou** o arquivo (`skipped-unparseable`) em vez de gravar dado no mês errado. | Aceito como residual — 1 de 38 meses (97,4% de cobertura); corrigir exigiria detectar/tratar mais uma variante de layout, não vale o retorno para 1 mês |

### Resultado real verificado (BigQuery, `brasil2036-dev`)

- **37 de 38 meses carregados** (jun/2023–jul/2026, exceto jun/2024 — achado #16).
- **15.142 linhas Gold**, **15.142 linhas de provenance** — cobertura de provenance 100% em toda a
  história real carregada, não só no mês de teste.
- **18.744.424 indeferimentos** somados no período (jun/2023–jul/2026) — número real, não estimado.
- **Dado da dívida confirmadamente intacto** depois de processar 37 meses reais de um 2º dataset:
  `metric_provenance` ainda com as 27 linhas de `divida_consolidada` — a correção crítica do achado
  #1 (PR1) provada em escala real, não só no teste de 1 mês.
- Tempo real: ~2,5–3 min/mês (arquivo XLSX ~67 MB) → **~100 min para as 37 execuções**.

---

## 5. Blockers / trabalho restante

- **Backfill real de Emitidos e Mantidos ainda não executado** — Indeferidos (o menor dos 3,
  ~2,5 GB no total) está completo e verificado; Emitidos (~30 GB, arquivos de até 7,4 GB/mês) e
  Mantidos (~60–90 GB, 3 sub-arquivos/mês) são ordens de grandeza maiores. Dado o ritmo observado em
  Indeferidos (~2,5–3 min por arquivo de 67 MB), arquivos de GB inteiros devem levar
  significativamente mais tempo por mês — a medir com `--limit 1` antes de comprometer a execução
  completa, mesma disciplina que funcionou para Indeferidos.
- **Até Emitidos/Mantidos rodarem, 2 dos 3 endpoints `/v1/metrics/{metric_id}/national` continuam
  devolvendo 404 em produção** (`inss_beneficios_emitidos` e `inss_beneficios_mantidos`); o de
  Indeferidos já responde com dado real. O módulo M03 mostra 1 número real + 2 "Indisponível" até lá.
- **Gate `integration` cobre só Emitidos** (1 dos 3 datasets, por decisão do DESIGN §6) — a fixture
  do CI continua sendo o único teste automatizado ponta a ponta para Emitidos; o backfill real de
  Emitidos ainda não rodou fora do CI.
- **Convergência de Mantidos (3 recursos/mês) validada só por raciocínio + teste unitário de
  Bronze** (`test_load_partition_scopes_by_source_uri_not_just_month`) — ainda não por uma execução
  real de backfill processando os 3 sub-arquivos de um mês em sequência.
- **e2e do web (`npm run e2e`) não executado nesta sessão** — precisa de `preview` + API viva;
  roda no `api-web.yml` pós-deploy, mesmo padrão do card da dívida.
- **Drill-down por UF/espécie na API não existe** — decisão deliberada (achado #10, YAGNI); só o
  agregado nacional está implementado. Extensível via `Config.metric_tables` sem quebrar nada.
- **Junho/2024 de Indeferidos não carregado** (achado #16) — 1 arquivo real com layout de coluna
  fora do padrão; residual aceito, 97,4% de cobertura histórica do dataset.

---

## 6. Status transitions

| Arquivo | Status | Próximo |
|---|---|---|
| `DEFINE_INSS_BENEFICIOS.md` | 🔶 PR1+PR2 Built (não `✅ Complete (Built)` — backfill real pendente) | backfill real, depois `/verify-spec` + `/ship` |
| `DESIGN_INSS_BENEFICIOS.md` | 🔶 PR1+PR2 Built (idem) | idem |

Não avancei para `✅ Complete (Built)` porque isso sinalizaria prontidão para `/ship`, o que seria
impreciso com o backfill real pendente (os 3 endpoints da API ainda devolvem 404 em produção sem
ele) — mesmo padrão de disciplina de status do `MVP_WALKING_SKELETON` (2 PRs antes do ship).

---

## 7. Quality gate (PR1 + PR2 — falta só o backfill real)

- [x] Todos os itens do manifesto criados/modificados (38 de 36 — 2 a mais não previstos: `Config.metric_tables`, achado #12)
- [x] `ruff` + `mypy --strict` + `pytest` verdes em `ingestion/` (64 testes) e `api/` (15 testes)
- [x] `web/` typecheck + build verdes, sem valor hard-coded
- [x] Sem TODO / sem segredo
- [x] Atribuição de agente (§1/§1b) + Autonomous Decisions (§4) — incluindo 1 achado crítico corrigido
- [x] Contratos e configs carregam sem erro
- [x] `terraform fmt` limpo
- [x] Gate `integration` provado contra BigQuery real (PR #4, 2 execuções verdes)
- [x] Rota da dívida comprovadamente não regride (`test_debt_route_unaffected_by_national_route`)
- [ ] `web/` e2e — pendente de deploy real (roda em `api-web.yml`)
- [ ] Backfill real executado e medido — **único bloqueador restante para `/ship`**
- [x] BUILD_REPORT gerado

---

## 8. Revision history

| Data | Versão | Mudança | Autor |
|---|---|---|---|
| 2026-09-04 | 1.0 | PR1 (espinha de dados) completo em `feature/inss-beneficios`: 3 conectores com schema real confirmado, correção crítica de `registry.py`/`provenance.py` (tabelas compartilhadas), `pipeline_incremental.py` novo, `backfill.py` resumível, 3 contratos + 6 SQL + 3 configs, Terraform redimensionado. 9 Autonomous Decisions, 1 crítica. `ruff`+`mypy`+`pytest` verdes (64 testes). PR2 e backfill real pendentes. | /build (Claude Sonnet 5) |
| 2026-09-04 | 1.1 | PR1 mergeado em `main` (#4), provado ao vivo contra BigQuery real. PR2 (API+web) completo em `feature/inss-beneficios-pr2`: rota `GET /v1/metrics/{metric_id}/national` (agregado nacional, resolvendo OQ1/OQ2 com YAGNI — achado #10), módulo M03 web (3 números, grace degradation), `Config.metric_tables` novo. `ruff`+`mypy`+`pytest` verdes em `api/` (15 testes) e `ingestion/`; `web` typecheck+build verdes. Rota da dívida comprovadamente intacta. Só o backfill histórico real falta para `/ship`. | /build (Claude Sonnet 5) |
| 2026-09-05 | 1.2 | PR2 mergeado. Backfill real de Indeferidos executado contra `brasil2036-dev` (37/38 meses, confirmação explícita do usuário em 2 etapas). Achados #13–16: bug crítico de path (`_REPO_INGESTION_ROOT`) nunca detectado por teste unitário até rodar de verdade; `period_resolver` novo (nomes de arquivo de Indeferidos não têm padrão YYYYMM, período lido do conteúdo real); ineficiência de `limit` corrigida; 1 arquivo real com layout fora do padrão (jun/2024) rejeitado com segurança. Dado da dívida confirmadamente intacto em escala real (37 meses, não só 1). Emitidos/Mantidos ainda pendentes. | /build (Claude Sonnet 5) |
