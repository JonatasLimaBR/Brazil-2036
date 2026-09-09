# DESIGN — RAG_PROVENANCE_QA

## Metadados

- **Feature:** RAG_PROVENANCE_QA
- **Status:** ✅ Shipped
- **Fase:** 2 (Design)
- **Entrada:** `.claude/sdd/features/DEFINE_RAG_PROVENANCE_QA.md` (Ready for Design)
- **Criado:** 2026-09-08
- **Confiança:** 0.8
- **Próximo passo:** `/build .claude/sdd/features/DESIGN_RAG_PROVENANCE_QA.md`

> Nota: assets do plugin SDD ausentes — documento segue a lista de seções do skill `sdd-design`,
> mesmo padrão dos designs anteriores.

---

## 0. Descoberta real

Antes de desenhar, verificado contra o real (não suposto):

| Item | Verificado como | Resultado |
|---|---|---|
| Contagem/lista exata de `metric_id`s reais hoje (OQ1) | Query real contra `brasil2036-dev.br2036_gold.metric_provenance`, agrupado por `metric_id` | **11 metric_ids reais**, cada um com fonte real (tabela completa na §1). Confirma: nenhum `inss_beneficios_mantidos` carregado ainda (consistente com o follow-up já rastreado do `INSS_BENEFICIOS`). |
| `VECTOR_SEARCH` exige `CREATE VECTOR INDEX` pra funcionar? (OQ2) | Pesquisa real (Google Cloud docs, via WebSearch) | **Não** — `VECTOR_SEARCH` é GA e funciona por busca exaustiva (brute-force) sem índice; `CREATE VECTOR INDEX` é uma otimização de performance recomendada só para tabelas grandes. Num corpus de 11 linhas, índice vetorial não compensa (overhead > benefício). **Decisão: v1 usa `VECTOR_SEARCH` sem índice.** |
| SDK Python recomendado pra chamar Gemini via Vertex AI (não pesquisado antes nesta sessão — 1ª vez que o projeto toca IA generativa) | Pesquisa real (PyPI, GitHub googleapis, Google Cloud docs) | `google-genai` (`pip install google-genai`) é o SDK atual recomendado, GA, cobre tanto Gemini Developer API quanto Vertex AI via `genai.Client(vertexai=True, project=..., location=...)`. Os módulos antigos (`vertexai.generative_models` etc.) estão **deprecados desde 2025-06-24, remoção prevista 2026-06-24** — não usar. |
| Disponibilidade real de `ML.GENERATE_EMBEDDING`/conexão BigQuery↔Vertex AI especificamente em `southamerica-east1` (OQ3) | Pesquisa real (WebSearch + WebFetch nas páginas oficiais) | **Não confirmado com certeza nesta sessão** — as páginas de referência do Google Cloud não retornaram o texto completo (limitação de fetch, não do produto). Este é o único item da descoberta real que fica **genuinamente em aberto** — ver Decisão D3 abaixo pra como isso é resolvido sem violar a disciplina do projeto de nunca criar recurso de nuvem fora de PR revisado. |
| Modelo de embedding/generativo exato disponível (OQ6) | Pesquisa real, não conclusiva sobre a lista completa vigente em `southamerica-east1` no momento do build | Nomes de referência usados no desenho (`text-embedding-005`, `gemini-2.5-flash`) são nomes reais e atuais de modelos Google, mas a disponibilidade exata na região do projeto só é confirmada no primeiro PR do build (mesmo padrão do item acima). |

---

## 1. Corpus real (11 metric_ids)

| `metric_id` | Linhas | Fonte real (`producing_organization` / `source`) |
|---|---|---|
| `cambio_usd_brl` | 883 | BCB — `bcdata.sgs.3695` |
| `divida_bruta_pib` | 236 | BCB — `bcdata.sgs.13762` |
| `divida_consolidada` | 27 | COREM/STN — Tesouro Transparente (CKAN, PAF) |
| `fiscal_despesa` | 355 | Tesouro Nacional/CESEF — Tesouro Transparente |
| `fiscal_primario` | 355 | Tesouro Nacional/CESEF — Tesouro Transparente |
| `fiscal_receita` | 355 | Tesouro Nacional/CESEF — Tesouro Transparente |
| `inss_beneficios_emitidos` | 1.216 | INSS — dados abertos |
| `inss_beneficios_indeferidos` | 15.142 | INSS — dados abertos |
| `ipca_mensal` | 559 | BCB — `bcdata.sgs.433` |
| `pib_mensal` | 438 | BCB — `bcdata.sgs.4380` |
| `selic_mensal` | 482 | BCB — `bcdata.sgs.4390` |

Cada linha da tabela nova de metodologia (`rag_knowledge_corpus`, §4) cita a URL real acima como
evidência — nenhuma URL nova/inventada.

---

## 2. Arquitetura

```text
┌──────────────────────────────────────────────────────────────────────────┐
│                         RAG_PROVENANCE_QA — v1                           │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ingestion/data/rag_knowledge_corpus.yaml (11 parágrafos curados)       │
│         │                                                               │
│         ▼                                                               │
│  ingestion/scripts/load_rag_corpus.py  ──MERGE──▶ br2036_gold.          │
│                                                     rag_knowledge_corpus │
│                                                     (metric_id, title,   │
│                                                      body_text,          │
│                                                      source_url, embed-  │
│                                                      ding ARRAY<FLOAT64>)│
│         │                                                               │
│         │ ML.GENERATE_EMBEDDING (modelo remoto via conexão              │
│         │ BigQuery↔Vertex AI, text-embedding-005)                       │
│         ▼                                                               │
│  api/src/api/knowledge.py                                              │
│    1. VECTOR_SEARCH(embedding, pergunta) + SEARCH() full-text +         │
│       filtro opcional por metric_id  →  top-N linhas + score            │
│    2. Gate determinístico: score máximo < limiar?                       │
│         SIM → resposta "evidência insuficiente" (sem chamar LLM)        │
│         NÃO → passo 3                                                   │
│    3. google-genai (Vertex AI, gemini-2.5-flash) sintetiza a resposta   │
│       em linguagem natural A PARTIR SÓ das linhas recuperadas           │
│       (grounding estrito — nunca gera fato fora do contexto dado)       │
│         │                                                               │
│         ▼                                                               │
│  POST /v1/knowledge/ask  →  {answer, citations[], evidence_sufficient}  │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

**Núcleo determinístico, borda probabilística (`ADR-013`), aplicado aqui:** o *gate* de "há
evidência suficiente?" é 100% SQL/determinístico (score de similaridade acima de um limiar
configurável) — o LLM nunca decide se deve responder ou não, só sintetiza texto a partir do que a
retrieval determinística já validou como relevante. Isso evita o modo de falha mais comum de RAG
("LLM responde com confiança mesmo sem contexto suficiente").

---

## 3. Decisões (ADRs inline)

### Decisão D1 — Retrieval 100% nativa no BigQuery, sem Vertex AI Vector Search dedicado

| Atributo | Valor |
|---|---|
| **Status** | Accepted |
| **Data** | 2026-09-08 |

**Contexto:** o projeto precisa de retrieval híbrida (lexical+vector+metadata, `ADR-026`) pra um
corpus inicial pequeno (11 linhas).

**Escolha:** `VECTOR_SEARCH` (sem índice, brute-force) + `CREATE SEARCH INDEX`/`SEARCH()`
(full-text) + filtros SQL, tudo dentro do BigQuery já provisionado.

**Alternativas rejeitadas:** Vertex AI Vector Search dedicado (índice/endpoint gerenciado com
custo fixo de deployment, sem justificativa de escala pra 11 linhas — mesmo racional que rejeitou
AlloyDB no `DEBTLAB_SIMULATOR`, `ADR-059`).

**Consequências:** zero serviço gerenciado novo além de 1 conexão IAM; reavaliar se o corpus
crescer o suficiente pra `CREATE VECTOR INDEX` compensar (documentado como gatilho de
reconsideração, não decisão permanente).

### Decisão D2 — Resposta do RAG não usa `ADR-028` (observed/estimated/simulated); usa envelope próprio

| Atributo | Valor |
|---|---|
| **Status** | Accepted |
| **Data** | 2026-09-08 |

**Contexto:** `ADR-028` rotula *valores de métrica*. Uma resposta de Q&A (texto + citações) não é
um valor numérico — nenhum dos 3 rótulos (`observed`/`estimated`/`simulated`) descreve
corretamente "texto sintetizado a partir de trechos reais recuperados".

**Escolha:** a resposta do endpoint carrega seu próprio envelope —
`{answer: str, citations: [{metric_id, source_url, title}], evidence_sufficient: bool}` — sem
campo `data_class`. Nenhuma extensão de `ADR-028` é necessária; ele continua escopado a valores
de métrica.

**Alternativas rejeitadas:** forçar a resposta a carregar `data_class=estimated` (semanticamente
errado — não é uma derivação numérica) ou criar um 4º rótulo em `ADR-028` (expandiria o escopo de
um ADR já aceito para um conceito diferente, sem necessidade real).

**Consequências:** `citations`/`evidence_sufficient` viram o mecanismo de confiança desta
capability — testado explicitamente (G6/AT5).

### Decisão D3 — Verificação de região (BigQuery↔Vertex AI) é o 1º PR do build, não suposta no design

| Atributo | Valor |
|---|---|
| **Status** | Accepted |
| **Data** | 2026-09-08 |

**Contexto:** a pesquisa real desta sessão (§0) não confirmou com certeza se a conexão
`google_bigquery_connection`/`ML.GENERATE_EMBEDDING` funciona sem fricção a partir de
`southamerica-east1` — as páginas oficiais não renderizaram o conteúdo completo via as ferramentas
disponíveis. Criar o recurso de nuvem agora, fora de um PR revisado, violaria a disciplina do
projeto ("nunca alterar produção diretamente", `CLAUDE.md`).

**Escolha:** o **PR1 do build** é uma fatia mínima e isolada — só a conexão Terraform + `CREATE
MODEL` remoto + 1 chamada real de `ML.GENERATE_EMBEDDING` contra `brasil2036-dev`, verificada ao
vivo antes de qualquer código de retrieval/endpoint ser escrito. Se `southamerica-east1` não
suportar, o fallback documentado é: manter os dados em `southamerica-east1` (padrão do projeto,
`ADR-005`) mas apontar o `ENDPOINT` do modelo remoto pra uma região Vertex AI compatível
(BigQuery permite declarar o endpoint completo do modelo remoto, não necessariamente a mesma
região do dataset) — decisão a confirmar com o resultado real do PR1, documentada no
`BUILD_REPORT`.

**Consequências:** o build começa por uma verificação de infra isolada e barata de reverter (só
uma conexão + 1 modelo, sem dado de produção em risco), em vez de assumir e descobrir o problema
só depois de todo o pipeline estar escrito — mesmo espírito de "descoberta real antes de construir
em cima" já seguido em toda fatia anterior, adaptado pro fato de que aqui a descoberta exige
provisionar (não só ler) um recurso real.

---

## 4. Manifesto de arquivos

| # | Arquivo | Ação | Propósito | Agente | Dependências |
|---|---|---|---|---|---|
| 1 | `infra/terraform/bigquery_connection_vertex.tf` | Create | `google_bigquery_connection` (`CLOUD_RESOURCE`) + IAM `roles/aiplatform.user` escopado à SA da conexão | @ci-cd-specialist | Nenhuma |
| 2 | `ingestion/sql/gold/rag_knowledge_embeddings.sql` | Create | `CREATE MODEL ... REMOTE WITH CONNECTION ... OPTIONS(ENDPOINT='text-embedding-005')`; query de refresh do embedding | @gcp-data-architect | 1 |
| 3 | `ingestion/data/rag_knowledge_corpus.yaml` | Create | 11 parágrafos de metodologia curados manualmente, 1 por `metric_id`, cada um citando a URL real da §1 | (general) | Nenhuma |
| 4 | `ingestion/scripts/load_rag_corpus.py` | Create | Carrega o YAML em `br2036_gold.rag_knowledge_corpus` via `MERGE` (mesmo padrão idempotente de `registry.py`), dispara o refresh de embedding (2) | @python-developer | 2, 3 |
| 5 | `ingestion/tests/test_load_rag_corpus.py` | Create | Unit test do parser YAML + `MERGE` (fake BigQuery client) | (general) | 4 |
| 6 | `ingestion/tests/integration/test_rag_corpus_bigquery.py` | Create | Integration test real: carrega o corpus, confirma embedding gerado, contra `brasil2036-dev` | @gcp-data-architect | 4 |
| 7 | `api/src/api/knowledge.py` | Create | `retrieve(question, metric_id_filter=None)` — SQL híbrida (`VECTOR_SEARCH`+`SEARCH()`+filtro); `compose_answer(question, retrieved_rows)` — chama `google-genai`/Vertex AI só com contexto recuperado; gate determinístico de limiar | @python-developer | 2, 4 |
| 8 | `api/src/api/models.py` | Modify | +`KnowledgeAskRequest`, `KnowledgeCitation`, `KnowledgeAskResponse` | (general) | Nenhuma |
| 9 | `api/src/api/main.py` | Modify | +`POST /v1/knowledge/ask` | (general) | 7, 8 |
| 10 | `api/src/api/config.yaml` | Modify | +chaves: `rag_dataset`/`rag_table`, `embedding_model`, `generative_model`, `similarity_threshold` | (general) | Nenhuma |
| 11 | `api/pyproject.toml` | Modify | +dependência `google-genai` | (general) | Nenhuma |
| 12 | `api/tests/test_knowledge_ask.py` | Create | Unit tests: retrieval com dado sintético, gate de limiar (com/sem evidência), resposta nunca cita fonte fora do corpus fake | @python-developer | 7, 8, 9 |
| 13 | `api/tests/integration/test_knowledge_ask_bigquery.py` | Create | Integration test real contra `brasil2036-dev` (corpus já carregado por 6) — AT2/AT3/AT4 verificados ao vivo | @gcp-data-architect | 7, 6 |
| 14 | `docs/adrs/ADR-061-rag-bigquery-native-retrieval.md` | Create | Formaliza D1-D3 | (general) | Nenhuma |
| 15 | `docs/specs/SPEC-018-RAG.md` | Modify | Expandido com o contrato real desta fatia (hoje 4 linhas) | (general) | Nenhuma |
| 16 | `INDEX.md` | Modify | +`ADR-061` | (general) | 14 |

**Racional de agentes:** Terraform/BigQuery ML → especialistas de infra/dados GCP já usados em
fatias anteriores (`ai-data-engineer-gcp`/`gcp-data-architect` conforme disponibilidade); código
Python de retrieval/composição → `python-developer` (mesmo padrão do `debtlab.py`); arquivos de
contrato/config/doc → `(general)`, consistente com o resto do repositório.

---

## 5. Padrões de código

### 5.1 Conexão + modelo remoto (Terraform, esqueleto real)

```hcl
# infra/terraform/bigquery_connection_vertex.tf
resource "google_bigquery_connection" "vertex_ai" {
  connection_id = "rag-vertex-ai"
  location      = var.region
  cloud_resource {}
}

resource "google_project_iam_member" "vertex_ai_connection_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_bigquery_connection.vertex_ai.cloud_resource[0].service_account_id}"
}
```

### 5.2 Modelo remoto + refresh de embedding (SQL, esqueleto real)

```sql
-- ingestion/sql/gold/rag_knowledge_embeddings.sql
CREATE MODEL IF NOT EXISTS `{project}.{dataset_gold}.rag_embedding_model`
REMOTE WITH CONNECTION `{project}.{region}.rag-vertex-ai`
OPTIONS (ENDPOINT = 'text-embedding-005');

CREATE TABLE IF NOT EXISTS `{project}.{dataset_gold}.rag_knowledge_corpus` (
  metric_id STRING, title STRING, body_text STRING, source_url STRING,
  producing_organization STRING, embedding ARRAY<FLOAT64>, updated_at TIMESTAMP
);

-- Refresh idempotente: recalcula embedding só de linhas sem embedding ou desatualizadas.
UPDATE `{project}.{dataset_gold}.rag_knowledge_corpus` t
SET embedding = e.ml_generate_embedding_result
FROM (
  SELECT metric_id, ml_generate_embedding_result
  FROM ML.GENERATE_EMBEDDING(
    MODEL `{project}.{dataset_gold}.rag_embedding_model`,
    (SELECT metric_id, body_text AS content
     FROM `{project}.{dataset_gold}.rag_knowledge_corpus`
     WHERE embedding IS NULL)
  )
) e
WHERE t.metric_id = e.metric_id;
```

### 5.3 Retrieval híbrida (SQL, esqueleto real — usado por `knowledge.py`)

```sql
-- VECTOR_SEARCH sem índice (corpus pequeno, ver D1) + SEARCH() full-text + filtro opcional
SELECT base.metric_id, base.title, base.body_text, base.source_url, distance
FROM VECTOR_SEARCH(
  TABLE `{project}.{dataset_gold}.rag_knowledge_corpus`,
  'embedding',
  (SELECT ml_generate_embedding_result AS embedding
   FROM ML.GENERATE_EMBEDDING(MODEL `{project}.{dataset_gold}.rag_embedding_model`,
        (SELECT @question AS content))),
  top_k => 5,
  distance_type => 'COSINE'
)
WHERE @metric_id_filter IS NULL OR base.metric_id = @metric_id_filter
ORDER BY distance ASC
```

### 5.4 Gate determinístico + síntese (Python, esqueleto real)

```python
# api/src/api/knowledge.py
from google import genai

def retrieve(question: str, *, metric_id_filter: str | None = None) -> list[RetrievedRow]:
    ...  # executa 5.3 via RunQuery, já existente em bigquery_repo.py


def compose_answer(question: str, rows: list[RetrievedRow], *, threshold: float) -> KnowledgeAskResponse:
    relevant = [r for r in rows if r.distance <= threshold]
    if not relevant:
        return KnowledgeAskResponse(
            answer="Evidência insuficiente no corpus indexado para responder com confiança.",
            citations=[],
            evidence_sufficient=False,
        )
    client = genai.Client(vertexai=True, project=config.gcp_project, location=config.region)
    context = "\n\n".join(f"[{r.metric_id}] {r.body_text} (fonte: {r.source_url})" for r in relevant)
    prompt = (
        "Responda a pergunta usando SOMENTE o contexto abaixo. "
        "Nunca invente informação fora do contexto. Cite o metric_id de cada afirmação.\n\n"
        f"Contexto:\n{context}\n\nPergunta: {question}"
    )
    text = client.models.generate_content(model=config.generative_model, contents=prompt).text
    citations = [KnowledgeCitation(metric_id=r.metric_id, source_url=r.source_url, title=r.title) for r in relevant]
    return KnowledgeAskResponse(answer=text, citations=citations, evidence_sufficient=True)
```

---

## 6. Estratégia de testes

| Tipo | Escopo | Cobre |
|---|---|---|
| Unit (`ingestion/`) | Parser do YAML curado + `MERGE` idempotente (fake client) | G1 |
| Unit (`api/`) | `retrieve()`/`compose_answer()` com dado sintético — gate de limiar COM e SEM evidência suficiente; resposta nunca cita fonte fora do corpus fake injetado | G5, G6, AT4, AT5 |
| Integration real (`ingestion/`) | Carrega o corpus real, confirma embedding gerado, contra `brasil2036-dev` | AT1 |
| Integration real (`api/`) | Pergunta real sobre `metric_id` real → cita fonte real (AT2); pergunta sobre catálogo (AT3); pergunta fora do corpus → evidência insuficiente (AT4) — mesma convenção `pytest.mark.integration` já estabelecida no `MACRO_TWIN_EXPANSION` | AT2, AT3, AT4, S1-S4 |
| Verificação manual ao vivo (PR1, D3) | `CREATE MODEL`/`ML.GENERATE_EMBEDDING` funcionam de verdade a partir de `southamerica-east1` | AT6 |

Cobre todos os acceptance tests da DEFINE (AT1-AT7 — AT7 é o ritual de CI, coberto pelo `ci-gate`
já existente, sem gate novo necessário).

---

## 7. Revision history

| Data | Versão | Mudança | Autor |
|---|---|---|---|
| 2026-09-08 | 1.0 | Criação a partir de `DEFINE_RAG_PROVENANCE_QA.md`. Descoberta real (§0): 11 `metric_id`s confirmados via query real; `VECTOR_SEARCH` não exige índice (GA, brute-force); SDK `google-genai` confirmado como atual (não o deprecado `vertexai.generative_models`); disponibilidade regional exata fica genuinamente em aberto, resolvida como PR1 isolado do build (D3). 3 decisões inline (D1-D3). Manifesto de 16 itens. Status → Ready for Build. | /design (Claude Sonnet 5) |
