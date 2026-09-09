# BUILD REPORT — RAG_PROVENANCE_QA

## Metadados

- **Feature:** RAG_PROVENANCE_QA
- **Fase:** 3 (Build)
- **Entrada:** `.claude/sdd/features/DESIGN_RAG_PROVENANCE_QA.md` (Ready for Build)
- **Branch:** `feature/rag-provenance-qa` (#43, PR1), `feature/rag-provenance-qa-pr2` (#44, PR2), PR3 (esta branch)
- **Data:** 2026-09-08
- **Status da build:** ✅ Completo (PR1 infra + PR2 corpus/embeddings + PR3 retrieval/endpoint) —
  pronto para `/verify-spec`
- **Próximo passo:** `/verify-spec` (sessão nova, read-only) → `/ship`

---

## 1. Task execution

### PR1 (#43) — Conexão BigQuery↔Vertex AI (infra spike, DESIGN D3)

| # | Arquivo | Ação | Nota |
|---|---|---|---|
| 1 | `infra/terraform/bigquery_connection_vertex.tf` | Create | `google_bigquery_connection` (`CLOUD_RESOURCE`) + `roles/aiplatform.user` na SA da conexão |
| 2 | `infra/terraform/apis.tf` | Modify | +`bigqueryconnection.googleapis.com`, +`aiplatform.googleapis.com` |
| 3 | `ingestion/scripts/verify_rag_embedding_connection.py` | Create | `CREATE MODEL` + 1 chamada real de `ML.GENERATE_EMBEDDING` para verificação ao vivo |

**Achado real:** 1ª tentativa de verificação ao vivo falhou (`does not have the permission to
access or use the endpoint`) — propagação de IAM para uma service account recém-criada, não um
bloqueio real de região. Confirmado com retry (8 tentativas, 20s de intervalo): **PASS** após
~80s, `southamerica-east1` funciona sem workaround.

### PR2 (#44) — Corpus curado + embeddings reais

| # | Arquivo | Ação | Nota |
|---|---|---|---|
| 4 | `ingestion/data/rag_knowledge_corpus.yaml` | Create | 11 parágrafos reais, 1 por `metric_id` já ingerido |
| 5 | `ingestion/src/ingestion/rag_corpus.py` | Create | `load_notes`, `fetch_current_sources` (JOIN com `metric_provenance` no load, não hardcoded), `upsert_corpus` (MERGE), `refresh_embeddings` |
| 6 | `ingestion/scripts/load_rag_corpus.py` | Create | CLI que encadeia os 3 passos acima |
| 7 | `ingestion/tests/test_rag_corpus.py` | Create | 6 unit tests (fake BigQuery) |
| 8 | `ingestion/tests/integration/test_rag_corpus_bigquery.py` | Create | Integration real (dataset isolado `citest_*`), inclui reverificação de idempotência |

**Achado real crítico, corrigido antes do merge:** `refresh_embeddings()` filtrava
`WHERE embedding IS NULL` (mesmo padrão de `provenance.py`/`registry.py` para colunas escalares).
Testado ao vivo contra `brasil2036-dev` antes de escrever o resto do pipeline (disciplina D3):
BigQuery armazena um `ARRAY<FLOAT64>` `NULL` como array vazio (`[]`), nunca `NULL` de verdade —
`IS NULL` combinaria zero linhas para sempre, tornando o refresh um no-op silencioso permanente
(sem erro, nada que um mock pegaria). Corrigido para `ARRAY_LENGTH(embedding) = 0 OR ... IS NULL`,
reverificado ao vivo (idempotência incluída).

**Backfill real confirmado:** `load_rag_corpus.py` rodado contra `brasil2036-dev` —
`loaded=11 pending_embeddings=0`. Verificado ao vivo: 11 `metric_id`s, todos com `source_url` real
e embedding de 768 dimensões.

### PR3 (esta branch) — Retrieval + endpoint + síntese de resposta

| # | Arquivo | Ação | Nota |
|---|---|---|---|
| 9 | `api/src/api/knowledge.py` | Create | `retrieve()` (VECTOR_SEARCH + filtro), `compose_answer()` (gate determinístico + síntese), `build_genai_generate()` |
| 10 | `api/src/api/bigquery_repo.py` | Modify | +propriedade pública `run_query` (evita 2º `bigquery.Client`) |
| 11 | `api/src/api/models.py` | Modify | +`KnowledgeAskRequest`, `KnowledgeCitation`, `KnowledgeAskResponse` |
| 12 | `api/src/api/main.py` | Modify | +`POST /v1/knowledge/ask` |
| 13 | `api/src/api/config.py`/`config.yaml` | Modify | +chaves RAG (`rag_similarity_threshold=0.45`, calibrado empiricamente — ver `§2`), +`gcp_region` (novo campo, `api-web.yml` não passa `GCP_REGION`) |
| 14 | `api/pyproject.toml` | Modify | +`google-genai>=1.0` |
| 15 | `api/tests/test_knowledge.py` | Create | 7 unit tests (gate nunca chama LLM sem evidência, citação só de nota relevante) |
| 16 | `api/tests/test_knowledge_endpoint.py` | Create | 5 testes de endpoint (DI overrides) |
| 17 | `api/tests/integration/test_knowledge_ask_bigquery.py` | Create | 3 testes reais (retrieval + pipeline completo com Gemini real) |
| 18 | `infra/terraform/cloud_run_services.tf` | Modify | +`roles/aiplatform.user` para `api-runtime` (chamada direta ao Gemini, separada da conexão da PR1) |
| 19 | `docs/adrs/ADR-061-rag-bigquery-native-retrieval.md` | Create | Formaliza D1-D3 do DESIGN |
| 20 | `docs/specs/SPEC-018-RAG.md` | Modify | Expandido de 4 linhas para o contrato real |
| 21 | `INDEX.md` | Modify | +`ADR-061` |
| 22 | `api/openapi/openapi.json` + `web/src/api-client/schema.d.ts` | Modify (regenerado) | Regenerados nesta mesma PR |

---

## 2. Achados técnicos durante o build (não previstos em detalhe pelo DESIGN)

### Achado #1 — limiar de similaridade calibrado empiricamente, não suposto

O DESIGN deixava o valor exato de `rag_similarity_threshold` como decisão de implementação.
Calibrado ao vivo contra o corpus real de 11 notas: perguntas genuinamente relevantes ("por que a
dívida bruta é calculada assim", "quanto é a taxa selic") pontuaram distância de cosseno
0.30–0.42; perguntas irrelevantes ("como fazer um bolo de chocolate", "receita da copa do mundo")
pontuaram 0.53–0.57. `0.45` fica no meio real dessa distância — documentado em `ADR-061` e no
comentário de `config.py`, não um número arbitrário.

### Achado #2 — bug real de BigQuery em `refresh_embeddings()` (detalhado em §1, PR2)

Já registrado acima; repetido aqui por ser o achado mais significativo do build.

### Achado #3 — `google-genai` é o SDK correto, `vertexai.generative_models` está deprecado

Pesquisa real (não suposição, 1ª vez que o projeto toca IA generativa): `vertexai.generative_models`
e módulos irmãos estão deprecados desde 2025-06-24, remoção prevista 2026-06-24. `google-genai`
(`genai.Client(vertexai=True, ...)`) é o SDK atual, GA, confirmado funcionando ao vivo contra
`southamerica-east1` (`gemini-2.5-flash`) antes de escrever `knowledge.py`.

### Achado #4 — filtro `@metric_id_filter IS NULL OR ...` combinado com `VECTOR_SEARCH` verificado ao vivo antes de escrever o código

Dado o histórico de 2 bugs reais de SQL nas 2 fatias anteriores (`MACRO_TWIN_EXPANSION`), a
combinação exata usada em `knowledge.py::retrieve()` (parâmetro NULL-ável + `VECTOR_SEARCH` +
`WHERE` externo) foi testada contra `brasil2036-dev` real antes de ser escrita no módulo — PASS
sem surpresas, mas a verificação evitou repetir o padrão dos 2 bugs anteriores.

---

## 3. Verification results

- **Ingestão (PR1+PR2):** `ruff check`/`format --check`/`mypy` limpos; `pytest` — 116 passed, 9
  deselected (integration). Integration real contra `brasil2036-dev` (`test_rag_corpus_bigquery.py`)
  — **PASS**, incluindo reverificação de idempotência. Backfill real confirmado (11/11 `metric_id`s,
  embeddings de 768 dims).
- **API (PR3):** `ruff check`/`format --check`/`mypy` limpos (9 arquivos fonte); `pytest` — 59
  passed, 1 deselected (0 regressão nos 47 pré-existentes). Integration real contra
  `brasil2036-dev` (`test_knowledge_ask_bigquery.py`, 3 casos) — **PASS**, incluindo o pipeline
  completo com uma chamada real ao Gemini via Vertex AI.
- **`web/`:** `npm run gen:client` + `typecheck` (`astro check`, 0 erros) + `build` verdes contra o
  `openapi.json` regenerado.
- **`terraform`:** `fmt -check` + `validate` (local, `-backend=false`) limpos para as 2 mudanças de
  infra (PR1 conexão, PR3 IAM do `api-runtime`).

---

## 4. Autonomous Decisions

| # | Decision Point | Options Considered | Chose | Rationale |
|---|----------------|--------------------|-------|-----------|
| 1 | `source_url` do corpus curado: hardcoded no YAML ou buscado de `metric_provenance` no load | (a) hardcoded no YAML; (b) buscado em `metric_provenance` a cada carga | (b) | Algumas fontes (série fiscal ampla) republicam sob nome de arquivo novo todo mês — uma URL fixa no texto versionado ficaria desatualizada no próximo backfill sem ninguém notar. |
| 2 | Filtro `WHERE embedding IS NULL` vs `ARRAY_LENGTH(embedding) = 0 OR IS NULL` | (a) `IS NULL` (padrão já usado para colunas escalares); (b) `ARRAY_LENGTH` | (b) | Testado ao vivo: (a) nunca combina nenhuma linha para arrays, tornaria o refresh um no-op silencioso permanente. |
| 3 | `rag_similarity_threshold` | (a) valor arbitrário/redondo (ex. 0.5); (b) calibrado contra o corpus real | (b) | Verificação ao vivo mostrou uma distância real clara entre relevante (≤0.42) e irrelevante (≥0.53) — usar essa distância real em vez de um número redondo não verificado. |
| 4 | `CREATE VECTOR INDEX` na v1 | (a) criar; (b) não criar | (b) | Pesquisa real confirmou que o índice é otimização, não pré-requisito; corpus de 11 linhas não se beneficia o suficiente para justificar a manutenção extra. |
| 5 | Resposta do RAG usa `ADR-028` ou envelope próprio | (a) forçar `data_class=estimated`; (b) envelope próprio (`citations`/`evidence_sufficient`) | (b) | Nenhum dos 3 rótulos de `ADR-028` descreve corretamente texto sintetizado a partir de trechos recuperados — forçar um seria uma classificação semanticamente errada. |
| 6 | Expor `run_query` de `BigQueryRepo` publicamente vs. construir um 2º `bigquery.Client` em `knowledge.py` | (a) 2º client; (b) propriedade pública `run_query` | (b) | Evita instanciar um 2º cliente BigQuery no mesmo processo sem necessidade real. |

---

## 5. Blockers / trabalho restante

Nenhum blocker. `ipca_mensal`/`selic_mensal`/`cambio_usd_brl`/`rag_knowledge_corpus` não estão
plugados no job noturno automático (`data.yml`) — mesmo padrão de débito já rastreado para as
fatias BCB anteriores; a metodologia curada muda raramente (só quando um `metric_id` novo é
ingerido), então este débito é de prioridade ainda mais baixa que o das séries numéricas.

---

## 6. Status transitions

| Arquivo | Status | Próximo |
|---|---|---|
| `DEFINE_RAG_PROVENANCE_QA.md` | ✅ Complete (Built) | `/verify-spec` → `/ship` |
| `DESIGN_RAG_PROVENANCE_QA.md` | ✅ Complete (Built) | idem |

---

## 7. Revision history

| Data | Versão | Mudança | Autor |
|---|---|---|---|
| 2026-09-08 | 1.0 | Build completo: PR1 (conexão BigQuery↔Vertex AI, infra spike verificada ao vivo) + PR2 (corpus curado de 11 notas reais + embeddings, bug real de `ARRAY_LENGTH` pego e corrigido antes do merge) + PR3 (retrieval híbrida + endpoint `POST /v1/knowledge/ask` + síntese via Gemini real, limiar de similaridade calibrado empiricamente). Todos os testes de integração rodados contra `brasil2036-dev` real, incluindo uma chamada real ao Gemini. 0 regressão em `ingestion/`/`api/`/`web/`. | /build (Claude Sonnet 5) |
