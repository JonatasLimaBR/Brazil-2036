# BUILD REPORT — INSS_BENEFICIOS

## Metadados

- **Feature:** INSS_BENEFICIOS
- **Fase:** 3 (Build)
- **Entrada:** `.claude/sdd/features/DESIGN_INSS_BENEFICIOS.md` (v1.0)
- **Branch:** `feature/inss-beneficios`
- **Data:** 2026-09-04
- **Status da build:** 🔶 **PR1 completo (espinha de dados), PR2 (API+web) e o backfill real ainda não executados.**
- **Próximo passo:** abrir PR1 → `ci-gate` verde → medir/reportar tempo real de 1 execução → PR2 (API+web) → rodar o backfill completo contra GCP real → `/verify-spec` → `/ship`.

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

### PR2 (API + web) — não iniciado nesta sessão
Itens 30–36 do manifesto do DESIGN (`bigquery_repo.py`, `models.py`, `main.py`, testes, módulo M03 web, cliente OpenAPI, e2e leve) permanecem pendentes. Dependem da Gold do PR1 já mergeada e (idealmente) de pelo menos 1 mês real carregado para validar contra dado de verdade.

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
| `integration` (BigQuery real) | — | ⚠️ **não executado** — precisa de `GCP_PROJECT`/WIF, indisponível nesta sessão interativa |
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

---

## 5. Blockers / trabalho restante

- **PR2 (API + web) não iniciado** — extensão do `BigQueryRepo`/endpoint para grão mês+espécie
  (G7/OQ1 do DEFINE), módulo M03 na Landing. Depende da Gold do PR1 já mergeada.
- **Backfill real não executado** — precisa de `GCP_PROJECT`/WIF reais (indisponível nesta sessão
  interativa) e é uma operação longa (~100–130 GB comprimidos, ~183 recursos) com custo/tempo não
  triviais. Por princípio de não tomar ações caras/difíceis de reverter sem confirmação explícita,
  **não foi disparado** — é o próximo passo concreto, de preferência via o workflow `data.yml`
  (ou uma execução dedicada), com tempo/custo reais medidos e reportados (DESIGN §7.4).
- **Gate `integration` cobre só Emitidos** (1 dos 3 datasets, por decisão do DESIGN §6) — Mantidos e
  Indeferidos têm cobertura unitária real (schemas confirmados, quirks tratados), mas não foram
  exercitados ponta a ponta contra BigQuery real nesta sessão.
- **Convergência de Mantidos (3 recursos/mês) validada só por raciocínio + teste unitário de
  Bronze** (`test_load_partition_scopes_by_source_uri_not_just_month`) — não por uma execução real
  de backfill processando os 3 sub-arquivos de um mês em sequência.

---

## 6. Status transitions

| Arquivo | Status | Próximo |
|---|---|---|
| `DEFINE_INSS_BENEFICIOS.md` | 🔶 PR1 Built (não `✅ Complete (Built)` — PR2 pendente) | PR2, depois `/ship` |
| `DESIGN_INSS_BENEFICIOS.md` | 🔶 PR1 Built (idem) | PR2, depois `/ship` |

Não avancei para `✅ Complete (Built)` porque isso sinalizaria prontidão para `/ship`, o que seria
impreciso com PR2 e o backfill real pendentes — mesmo padrão de disciplina de status do
`MVP_WALKING_SKELETON` (2 PRs antes do ship).

---

## 7. Quality gate (parcial — PR1)

- [x] Todos os itens do manifesto do PR1 criados/modificados (29, 1 dispensado por já existir)
- [x] `ruff` + `mypy --strict` + `pytest` verdes (64 testes)
- [x] Sem TODO / sem segredo
- [x] Atribuição de agente (§1) + Autonomous Decisions (§4) — incluindo 1 achado crítico corrigido
- [x] Contratos e configs carregam sem erro
- [x] `terraform fmt` limpo
- [ ] Gate `integration` provado contra BigQuery real — **pendente do PR** (mesmo padrão do CI_ASSURANCE_GATES)
- [ ] PR2 (API+web)
- [ ] Backfill real executado e medido
- [x] BUILD_REPORT gerado

---

## 8. Revision history

| Data | Versão | Mudança | Autor |
|---|---|---|---|
| 2026-09-04 | 1.0 | PR1 (espinha de dados) completo em `feature/inss-beneficios`: 3 conectores com schema real confirmado, correção crítica de `registry.py`/`provenance.py` (tabelas compartilhadas), `pipeline_incremental.py` novo, `backfill.py` resumível, 3 contratos + 6 SQL + 3 configs, Terraform redimensionado. 9 Autonomous Decisions, 1 crítica. `ruff`+`mypy`+`pytest` verdes (64 testes). PR2 e backfill real pendentes. | /build (Claude Sonnet 5) |
