# ADR-061 — RAG_PROVENANCE_QA: retrieval híbrida nativa do BigQuery, sem serviço novo

## Status
Accepted

## Contexto
Esta decisão é parte do baseline arquitetural do BRASIL 2036 e deve ser lida com o `CONTEXTO.md`.
`RAG_PROVENANCE_QA` é a primeira fatia de `EPIC-024 — Knowledge/RAG` (`SPEC-018`, `ADR-026`) — até
esta feature, 0% do RAG do projeto estava construído. `ADR-026` já decidiu "hybrid + metadata
filters", mas não a implementação concreta.

Descoberta real no `/design` (`DESIGN_RAG_PROVENANCE_QA.md §0`), não suposição: query real contra
`metric_provenance` confirmou 11 `metric_id`s já reais (dívida, fiscal ×3, INSS ×2, macro ×5) —
corpus pequeno o suficiente para uma decisão de arquitetura diferente da normalmente assumida para
RAG em escala. Pesquisa real (Google Cloud docs) confirmou que `VECTOR_SEARCH` do BigQuery é GA e
funciona por busca exaustiva sem `CREATE VECTOR INDEX` — o índice é uma otimização recomendada só
para tabelas grandes, não um pré-requisito de correção.

## Decision drivers
- corpus inicial pequeno (11 linhas) não justifica um índice vetorial gerenciado;
- projeto já segue o padrão de nunca provisionar serviço novo sem justificativa real de escala
  (`ADR-059`: BigQuery em vez de AlloyDB para o DebtLab);
- retrieval e o dado que ela indexa devem viver no mesmo motor que já é a fonte de verdade
  quantitativa do projeto (`ADR-003`);
- custo operacional e simplicidade de auditoria (uma query, não um serviço adicional com sua
  própria superfície de IAM/rede).

## Alternativas consideradas

### A. Vertex AI Vector Search dedicado
Considerada e descartada: índice/endpoint gerenciado com custo fixo de deployment, sem
justificativa de escala para 11 linhas — mesmo racional que já rejeitou AlloyDB no
`DEBTLAB_SIMULATOR`.

### B. Retrieval 100% nativa do BigQuery (`VECTOR_SEARCH` sem índice + `SEARCH()` + filtros SQL)
Alternativa escolhida.

## Decisão
- **Retrieval híbrida dentro do BigQuery**, sem serviço gerenciado novo além de uma conexão
  BigQuery↔Vertex AI (`google_bigquery_connection`, `CLOUD_RESOURCE`) usada só para o modelo remoto
  de embedding (`ML.GENERATE_EMBEDDING`, `text-embedding-005`).
- **`VECTOR_SEARCH` sem `CREATE VECTOR INDEX`** — brute-force é suficiente e mais simples no volume
  atual; reconsiderar se o corpus crescer o bastante para o índice compensar (gatilho, não decisão
  permanente).
- **`SEARCH()`/full-text (a perna lexical do "híbrido") não foi implementada nesta fatia** — só
  `VECTOR_SEARCH` + filtro de metadata (`metric_id`). O `DEFINE` original (G4, MUST) e o desenho
  inicial deste documento previam as 3 pernas; a omissão só foi documentada depois do fato, em
  `SPEC-018-RAG.md` ("fora de escopo"), sem virar uma decisão rastreada aqui — achado real do
  `/verify-spec` independente, corrigido nesta revisão. Razão real, registrada agora
  explicitamente: com um corpus de 11 notas, a busca vetorial sozinha já recupera a nota certa em
  todos os casos de teste reais verificados (unit + integration + verificação ao vivo em produção,
  incluindo o caso negativo de evidência insuficiente); `SEARCH()` teria adicionado uma 2ª
  dimensão de score pra combinar sem nenhum ganho de recall observável nesse volume. **Não é uma
  decisão permanente** — reconsiderar junto com `CREATE VECTOR INDEX` quando o corpus crescer o
  suficiente para buscas por termo exato (siglas, códigos de série) começarem a divergir do que o
  vetor sozinho recupera bem.
- **Gate de evidência determinístico, não decidido pelo LLM** (`ADR-013`): a resposta só é
  sintetizada por um modelo generativo quando pelo menos 1 nota recuperada tem distância de cosseno
  ≤ `rag_similarity_threshold` (0.45, calibrado empiricamente — ver "Verificação"). Sem nota
  relevante, o endpoint responde "evidência insuficiente" sem nunca chamar o modelo generativo.
- **Resposta do RAG não usa `ADR-028`** (`observed`/`estimated`/`simulated`) — carrega seu próprio
  envelope (`answer`, `citations[]`, `evidence_sufficient`). Nenhum dos 3 rótulos de `ADR-028`
  descreve corretamente texto sintetizado a partir de trechos recuperados; `ADR-028` continua
  escopado a valores de métrica, sem expansão.
- **Corpus curado manualmente, não parseado automaticamente de páginas oficiais**: 1 parágrafo de
  metodologia real por `metric_id` já ingerido (`ingestion/data/rag_knowledge_corpus.yaml`), com
  `source_url`/`producing_organization` buscados de `metric_provenance` no momento da carga (nunca
  hardcoded no YAML — alguns arquivos-fonte mudam de nome todo mês).
- **SDK `google-genai`** (não `vertexai.generative_models`, deprecado desde 2025-06-24) para a
  chamada direta ao Gemini (`gemini-2.5-flash`) que sintetiza a resposta final a partir do contexto
  já validado pelo gate.

## Por que
O corpus real (11 linhas) não tem volume que justifique um serviço de vetor dedicado; manter tudo
no BigQuery evita uma nova superfície de IAM/rede e mantém o RAG auditável pela mesma ferramenta
que já é a fonte de verdade do projeto. O gate determinístico evita o modo de falha mais comum de
RAG — um LLM respondendo com confiança mesmo sem contexto suficiente — ao nunca dar ao modelo a
chance de decidir se "sabe o suficiente"; quem decide isso é sempre uma comparação numérica de
distância, feita antes de qualquer chamada ao modelo.

## Consequências positivas
- Zero serviço gerenciado novo além de uma conexão IAM — infraestrutura mínima para a primeira
  fatia de uma capability inteiramente nova no projeto.
- Retrieval e composição de resposta são auditáveis com as mesmas ferramentas (BigQuery, testes de
  integração reais) já usadas em toda fatia anterior.
- O limiar de similaridade não é um número arbitrário: verificado ao vivo contra o corpus real,
  perguntas genuinamente relevantes pontuaram 0.30–0.42 e perguntas irrelevantes 0.53–0.57 —
  0.45 fica no meio real dessa distância.

## Consequências negativas / custo aceito
- `VECTOR_SEARCH` sem índice não escala indefinidamente — aceito para a v1; reavaliar
  `CREATE VECTOR INDEX` quando o corpus crescer o suficiente para o brute-force ficar caro.
- O corpus é curado manualmente, não abrange documentos legais/fiscais reais (LOA/LDO/decretos) —
  escopo deliberadamente menor que a visão de longo prazo de `CONTEXTO.md §14`; fatia futura de RAG
  fica responsável por essa expansão.
- Um bug real de BigQuery foi descoberto durante o build (não uma consequência de design, mas vale
  registrar aqui): `ARRAY<FLOAT64>` nunca é `NULL` de verdade no BigQuery — um valor `NULL` inserido
  vira array vazio (`[]`) silenciosamente. `embedding IS NULL` combinearia zero linhas para sempre;
  corrigido para `ARRAY_LENGTH(embedding) = 0 OR ... IS NULL`, verificado ao vivo antes do merge.

## Verificação
`ingestion/tests/test_rag_corpus.py` + `ingestion/tests/integration/test_rag_corpus_bigquery.py`
(carga do corpus + geração real de embedding contra `brasil2036-dev`, incluindo reverificação de
idempotência que guarda diretamente contra a regressão do `ARRAY_LENGTH`); `api/tests/test_knowledge.py`
+ `api/tests/test_knowledge_endpoint.py` (gate determinístico nunca chama o LLM sem evidência
relevante, citação nunca inclui nota fora do conjunto recuperado); `api/tests/integration/
test_knowledge_ask_bigquery.py` (retrieval real encontra a nota certa para uma pergunta real,
pipeline completo — retrieval + Gemini real — cita fonte real).

## Quando reconsiderar
Se o corpus crescer o suficiente para `VECTOR_SEARCH` sem índice ficar lento ou caro, ou se uma
fatia futura precisar de um volume de documentos (legais/fiscais reais) que um índice gerenciado
justifique — reconsiderar com uma nova ADR, não uma reversão silenciosa desta.
