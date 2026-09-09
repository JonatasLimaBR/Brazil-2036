# SPEC-018 — RAG

## Escopo realizado (RAG_PROVENANCE_QA, ADR-061)

Primeira fatia: RAG sobre proveniência/metodologia das métricas já reais deste projeto (não sobre
documentos legais/fiscais externos — ver "Fora de escopo" abaixo).

### Corpus

- Fonte: `metric_provenance`/`dataset_registry` (URLs/organização reais, já existentes desde a
  primeira fatia de dado) + 1 parágrafo de metodologia curado manualmente por `metric_id` já
  ingerido (`ingestion/data/rag_knowledge_corpus.yaml`).
- `source_url`/`producing_organization` nunca hardcoded no texto curado — buscados de
  `metric_provenance` no momento da carga (`ingestion/src/ingestion/rag_corpus.py`), porque
  algumas fontes republicam sob um nome de arquivo novo a cada mês.
- Tabela: `br2036_gold.rag_knowledge_corpus` (`metric_id`, `title`, `body_text`, `source_url`,
  `producing_organization`, `embedding ARRAY<FLOAT64>`, `updated_at`).

### Ingestão e embeddings

Documents are parsed as curated YAML entries (not scraped HTML/PDF in this slice), normalized,
loaded via `ingestion/scripts/load_rag_corpus.py`, embedded via `ML.GENERATE_EMBEDDING` (modelo
remoto `text-embedding-005`, conexão BigQuery↔Vertex AI `rag-vertex-ai`,
`infra/terraform/bigquery_connection_vertex.tf`) e indexados no BigQuery.

### Retrieval

Retrieval combines lexical/vector where supported plus filters by `metric_id` (metadata) —
`VECTOR_SEARCH` (COSINE, sem `CREATE VECTOR INDEX` — corpus pequeno, `ADR-061`) + filtro SQL
opcional por `metric_id`. `SEARCH()`/full-text fica fora desta fatia (corpus pequeno o bastante
para o vetor sozinho cobrir bem — reavaliar se o corpus crescer).

### Gate de evidência e resposta

- Gate determinístico (`ADR-013`): só sintetiza resposta quando pelo menos 1 nota recuperada tem
  distância de cosseno ≤ `rag_similarity_threshold` (default `0.45`, calibrado empiricamente contra
  o corpus real — ver `ADR-061`). O modelo generativo nunca decide se há evidência suficiente.
- Answers cite retrieved source metadata: toda resposta com `evidence_sufficient=true` carrega
  `citations[]` (`metric_id`, `title`, `source_url`) — cada `source_url` existe de verdade em
  `metric_provenance`/`rag_knowledge_corpus`, nunca fabricada (testado: `api/tests/test_knowledge.py`,
  `api/tests/integration/test_knowledge_ask_bigquery.py`).
- If evidence was insufficient, answer must say evidence was insufficient: quando nenhuma nota
  passa o limiar, a resposta é fixa ("Evidência insuficiente...") e `evidence_sufficient=false`,
  `citations=[]` — o modelo generativo nunca é chamado nesse caso.
- Síntese de resposta: `google-genai` (Vertex AI, `gemini-2.5-flash` por padrão), chamada só com o
  texto das notas já validadas pelo gate — nunca com contexto livre.

### Endpoint

`POST /v1/knowledge/ask` — `{question: str, metric_id?: str}` → `{answer, citations[],
evidence_sufficient}`. Classe READ (`AGENTS.md`) — sem escrita. Sem `data_class` (`ADR-028` cobre
valor de métrica, não texto sintetizado — ver `ADR-061`).

## Fora de escopo desta fatia

- `GraphService`/ontologia completa (`SPEC-019`, `EPIC-025`).
- Parsing automático de documentos legais/fiscais reais (leis, decretos, DOU, TCU, LOA/LDO —
  `CONTEXTO.md §14`) — corpus desta fatia é só metodologia curada das métricas já ingeridas.
- Chat multi-turn com memória de conversa.
- `CREATE VECTOR INDEX` — reavaliar quando o corpus crescer.

## Verificação

`ingestion/tests/test_rag_corpus.py`, `ingestion/tests/integration/test_rag_corpus_bigquery.py`,
`api/tests/test_knowledge.py`, `api/tests/test_knowledge_endpoint.py`,
`api/tests/integration/test_knowledge_ask_bigquery.py` — todos rodados contra `brasil2036-dev`
real onde aplicável (ver `ADR-061` para o detalhamento).
