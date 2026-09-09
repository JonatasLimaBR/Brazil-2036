# BRAINSTORM — RAG_PROVENANCE_QA

- **Feature:** RAG_PROVENANCE_QA
- **Status:** ✅ Shipped

- **Fase:** 0 (Brainstorm)
- **Criado:** 2026-09-08
- **Idioma:** PT-BR (alinhado a `docs/discovery/`)
- **Próximo passo:** `/define .claude/sdd/features/BRAINSTORM_RAG_PROVENANCE_QA.md`

> Nota: assets do plugin SDD ausentes (`kb/_index.yaml`, `BRAINSTORM_TEMPLATE.md` não instalados) —
> documento segue a lista de seções do skill `sdd-brainstorm`, mesmo padrão dos brainstorms
> anteriores.

---

## 1. Ideia

Primeira fatia de RAG do projeto (`EPIC-024 — Knowledge/RAG`, `SPEC-018`, `ADR-026`) — hoje 0%
construído. O `CONTEXTO.md §14` descreve o RAG do produto como sendo sobre documentos oficiais
reais (leis, decretos, portarias, notas técnicas, DOU, TCU, BCB, Tesouro, IPEA, PPA, LDO, LOA), não
sobre a documentação interna do próprio projeto — decisão confirmada com o usuário logo no início da
descoberta (rejeitado usar PRDs/ADRs/SPECs como corpus, por não ser o que o produto entrega ao
usuário final/avaliador CGU).

Em vez de partir para descoberta de fonte de documento legal/fiscal nova (LOA/LDO/decretos —
domínio totalmente não tocado, PDF/HTML de formatos variados, direito de uso a confirmar), o
usuário escolheu ancorar esta 1ª fatia no que o projeto já tem de real e verificado: as 7 fatias de
dado já shipadas (`MVP_WALKING_SKELETON`, `INSS_BENEFICIOS`, `FISCAL_RECEITA_DESPESA`,
`DEBTLAB_SIMULATOR`, `MACRO_TWIN_EXPANSION`) deixaram `metric_provenance`/`dataset_registry` cheios
de URLs oficiais reais (Tesouro Transparente, BCB SGS, INSS) para cada métrica, mas sem nenhum
texto explicativo de metodologia — hoje um usuário só vê "de onde veio o número" (a URL), nunca "por
que o número é calculado assim". Esta fatia entrega 1 endpoint de Q&A que responde isso, citando
fonte real, nunca fabricando.

**Escopo consolidado ao longo da descoberta, por decisão explícita do usuário em cada
checkpoint:**
1. Corpus: `metric_provenance`/`dataset_registry` (já reais) + parágrafos de metodologia curados
   manualmente por `metric_id`, cada um grounded numa página/nota oficial real (URL como evidência)
   — não parsing automático de HTML/PDF novo, não documentação interna do projeto.
2. Consumidor: 1 endpoint de Q&A unificado (não 3 endpoints separados) — responde pergunta livre,
   sempre citando fonte real ou dizendo que a evidência é insuficiente; a mesma retrieval também
   cobre "por que esse número é calculado assim" e "quais métricas existem" (o `dataset_registry`
   indexado junto cobre navegação de catálogo).
3. Arquitetura: tudo dentro do BigQuery (`ML.GENERATE_EMBEDDING` + `VECTOR_SEARCH` + `SEARCH()`
   full-text + filtros SQL) — zero serviço novo, mesmo padrão de "nunca provisionar infra nova sem
   justificativa real" já seguido no `DEBTLAB_SIMULATOR` (BigQuery em vez de AlloyDB).

---

## 2. Contexto técnico

| Aspecto | Observação |
|---|---|
| **Corpus estruturado já real** | `metric_provenance` (schema real, `ingestion/src/ingestion/provenance.py`): `metric_id`, `reference_date`, `value`, `unit`, `source` (URL real), `producing_organization`, `assumptions` (`ARRAY<STRING>`, já carrega texto real como `"value reported by the producing organization under the PAF"`), `confidence`, `scenario`. `dataset_registry` (`ingestion/src/ingestion/registry.py`): `dataset_id`, `resource_url`, `source_url`, `resource_format`, `organization`, `license`, `update_frequency`, `br2036_domain`, `br2036_module` — metadado estruturado, sem texto livre de descrição longa. |
| **Texto de metodologia — não existe ainda** | Nenhuma tabela hoje guarda um parágrafo explicativo real por `metric_id`. Precisa ser criado nesta fatia — curadoria manual, grounded na página oficial real de cada fonte (mesmo processo de "nunca supor, sempre inspecionar a fonte real" já seguido em toda ingestão anterior). |
| **BigQuery ML — nunca usado no projeto** | Primeira vez que o projeto toca `ML.GENERATE_EMBEDDING` (modelo remoto apontando pro Vertex AI text-embedding), `VECTOR_SEARCH`/`CREATE VECTOR INDEX`, e `CREATE SEARCH INDEX`/`SEARCH()` (full-text nativo do BigQuery). Recurso real do BigQuery (não fabricado), mas nunca provisionado aqui. |
| **Terraform — sem conexão BigQuery↔Vertex AI hoje** | `grep` em `infra/terraform/*.tf` por `vertex`/`aiplatform`/`connection` não retornou nada — confirma que o recurso `google_bigquery_connection` (tipo `CLOUD_RESOURCE`, com service account IAM `roles/aiplatform.user`) que `ML.GENERATE_EMBEDDING` exige via modelo remoto **não existe ainda**. É IaC genuinamente nova, não reaproveitável. |
| **`api-runtime` — permissão de escrita já existe, mas escopada** | Desde o `DEBTLAB_SIMULATOR`, `api-runtime` tem `roles/bigquery.dataEditor` escopado só a `br2036_control` (não a `br2036_gold`). Se o texto de metodologia curado for uma tabela nova em `br2036_gold` (mais natural, ao lado de `dataset_registry`/`metric_provenance`), o endpoint de leitura não precisa de escrita nova — só ingestão (via `ingestion/`, que já escreve em Gold) precisa gravar lá. |
| **`ADR-028` não cobre resposta de RAG** | `observed`/`estimated`/`simulated` são rótulos de **valor de métrica**, não de **resposta de Q&A com citação**. Uma resposta do RAG não é nenhum dos 3 — é um tipo de artefato novo (texto + lista de citações + flag de evidência insuficiente). Fica pro `/design` decidir se precisa de um rótulo próprio (`ADR-028` ganha uma 4ª categoria, ou nota separada) — não resolvido nesta sessão. |
| **`AGENTS.md` — classe de capability** | O endpoint é 100% leitura (busca + composição de resposta a partir de texto já indexado, sem gravar nada em resposta a uma pergunta) — cabe na classe READ já usada pelos endpoints `/v1/metrics/*`/`/v1/simulations/debtlab/{scenario_id}`, não precisa de DRAFT/PUBLISH/PRIVILEGED-SECURITY. |
| **Numeração livre** | `SPEC-018-RAG.md` já existe (hoje 4 linhas, esqueleto) — esta fatia expande esse SPEC em vez de criar um novo, mesmo padrão do `DEBTLAB_SIMULATOR` reaproveitando `SPEC-009`. Próximo ADR livre: `ADR-061` (depois de `ADR-060`). |

---

## 3. Discovery

| # | Pergunta | Resposta | Impacto no desenho |
|---|---|---|---|
| 1 | Qual corpus real serve de base pro RAG v1? | **Proveniência + metodologia das métricas já reais** (`metric_provenance`/`dataset_registry` + parágrafos curados) — não documentos legais/fiscais novos (LOA/decretos), não documentação interna do projeto. | Corpus fica 100% dentro do que o projeto já ingere de verdade; zero descoberta de fonte de documento nova. |
| 2 | Qual consumidor real justifica a fatia? | Usuário pediu inicialmente "todas as opções possíveis" (Q&A de proveniência, chat genérico, busca de catálogo) — validado com o usuário que, dado o corpus escolhido, as 3 colapsam num único endpoint de Q&A (a mesma retrieval híbrida serve as 3 perguntas). | 1 endpoint, não 3 — menos superfície de contrato/API, mesma cobertura funcional. |
| 3 | Qual arquitetura de retrieval pro híbrido lexical+vector+metadata? | **Tudo dentro do BigQuery** (`ML.GENERATE_EMBEDDING` + `VECTOR_SEARCH` + `SEARCH()` + filtros SQL) — não Vertex AI Vector Search dedicado. | Zero serviço gerenciado novo além de uma conexão BigQuery↔Vertex AI (IAM, não um índice/endpoint com custo fixo de deployment). |
| 4 | De onde vem o texto de metodologia que o RAG indexa e cita? | **Curadoria manual real por `metric_id`** — parágrafo curto, grounded na página oficial real de cada fonte, URL como evidência. Não parsing automático de HTML/PDF das páginas oficiais (rejeitado — escopo de descoberta novo significativo). | Nova tabela/arquivo de texto curado versionado no repo, não um pipeline de scraping novo. |
| 5 | Confirmação final da leitura consolidada (corpus + consumidor + arquitetura + fonte do texto)? | **Confirmado explicitamente** pelo usuário em checkpoint dedicado. | Escopo fechado para o `/define`. |

---

## 4. Inventário de amostras

| Tipo | Disponível? | Uso previsto |
|---|---|---|
| URLs de proveniência reais por métrica | Sim — `metric_provenance.source`, real desde `MVP_WALKING_SKELETON`, confirmado por schema (`provenance.py`). | Cada resposta do RAG cita a URL real como evidência, nunca uma URL genérica/fabricada. |
| `assumptions` reais já existentes em `metric_provenance` | Sim — `ARRAY<STRING>`, já carrega texto real por linha (ex.: metodologia PAF da dívida). | Fonte de texto adicional gratuita para o corpus — não precisa ser toda curada do zero; parte já existe. |
| Metadado estruturado de catálogo | Sim — `dataset_registry`, schema real confirmado (`registry.py`). | Indexado para responder "quais métricas de X existem" via filtro/busca estruturada, não vetor. |
| Parágrafos de metodologia livre por `metric_id` | **Não** — precisa ser escrito nesta fatia. | Curadoria manual, 1 por `metric_id` já real (dívida, fiscal ×3, INSS, macro ×5 — contagem exata a confirmar no `/design` com uma query real, não suposta aqui). |
| Precedente de BigQuery ML / embeddings no repo | Não — primeira vez. | `/design` precisa desenhar do zero a conexão BigQuery↔Vertex AI (Terraform) e o modelo remoto — sem KB específico de RAG/embeddings no projeto ainda. |

---

## 5. Abordagens exploradas

### Abordagem A — Corpus de proveniência real + retrieval híbrida 100% BigQuery ⭐ Escolhida
- **O quê:** indexar `metric_provenance` (incluindo `assumptions` já real) + `dataset_registry` +
  parágrafos de metodologia curados manualmente, tudo em tabelas Gold; `ML.GENERATE_EMBEDDING`
  gera os vetores, `VECTOR_SEARCH` faz a busca semântica, `SEARCH()` faz full-text, filtros SQL
  fazem metadata (por `metric_id`/organização/data) — 1 endpoint `GET`/`POST` de Q&A que combina os
  3 e sempre cita fonte real ou diz que a evidência é insuficiente.
- **Prós:** zero descoberta de fonte de documento nova (corpus já existe em parte); zero serviço
  gerenciado novo (só uma conexão IAM BigQuery↔Vertex AI); conecta o RAG diretamente ao
  diferencial de rastreabilidade que já é o núcleo do projeto; reaproveita 100% do padrão de
  "nunca fabricar dado oficial" já testado em 7 fatias anteriores.
- **Contras:** corpus pequeno pra uma 1ª fatia (poucas métricas × 1 parágrafo cada) — respostas
  vão cobrir um universo estreito de perguntas; primeira vez com BigQuery ML/embeddings no
  projeto, incerteza técnica real sobre `VECTOR_SEARCH` num dataset tão pequeno (índice vetorial
  pode nem compensar contra full-text simples nesse volume — decisão de desenho pro `/design`).
- **Confiança:** 0.8 — a parte de dado (corpus) é de baixo risco (dado já real), a parte de
  infra (BigQuery ML, conexão Vertex AI) é território novo, mas um recurso real e documentado do
  GCP, não uma aposta arquitetural.

### Abordagem B — Vertex AI Vector Search dedicado
- **O quê:** índice/endpoint gerenciado do Vertex AI Vector Search pro vetor, BigQuery só pra
  metadata/lexical.
- **Por que não escolhida:** cria um serviço novo com custo fixo/ongoing (deployment de índice)
  que nenhuma fatia anterior precisou — mesmo tipo de decisão que o projeto já rejeitou pro
  AlloyDB no `DEBTLAB_SIMULATOR` (`ADR-059`), por falta de justificativa de custo/escala real
  nesta fase do projeto.
- **Confiança:** 0.75 (mais robusto para escala futura) — mas não é a escolha do usuário agora.

### Abordagem C — Documentos legais/fiscais reais (LOA/LDO/decretos/notas técnicas), parsing real
- **O quê:** buscar e parsear as páginas/PDFs oficiais reais (Tesouro Transparente, DOU, TCU) para
  extrair texto de metodologia automaticamente, mais fiel à visão de `CONTEXTO.md §14`.
- **Por que não escolhida:** domínio de descoberta totalmente novo (onde baixar, formato
  PDF/HTML variado por fonte, direito de uso) — escopo de descoberta real significativamente
  maior que uma "1ª fatia básica"; usuário preferiu ancorar no dado já real primeiro.
- **Confiança:** 0.6 — mais fiel à visão de longo prazo do RAG do produto, mas risco de escopo
  alto para esta fatia especificamente; fica como direção natural de uma fatia futura de RAG.

---

## 6. Itens removidos / adiados (YAGNI)

| Item | Por que fora desta fatia | Vai para |
|---|---|---|
| `GraphService` (`ADR-027`, `EPIC-025`) — entidades/relações completas | Endpoint de Q&A não precisa de grafo pra responder sobre proveniência de métrica já plana (`metric_id` → fonte); grafo entra quando houver perguntas relacionais reais ("quem financia X", "o que depende de Y"). | `EPIC-025`, fatia futura, se houver consumidor real. |
| Parsing automático de HTML/PDF das páginas oficiais | Escopo de descoberta novo significativo (formatos variados por fonte); usuário preferiu curadoria manual real por enquanto. | Fatia futura de RAG, se a curadoria manual não escalar. |
| Documentos legais/fiscais novos (LOA/LDO/decretos/DOU/TCU) | Fora do corpus desta fatia — ver Abordagem C. | `EPIC-024`, fatia futura própria. |
| Chat multi-turn com memória de conversa | Endpoint de Q&A é single-turn (pergunta → resposta com citação); memória conversacional é escopo de UX/portal, não desta capability de retrieval. | Fatia futura de portal/chat, se pedida. |
| Vertex AI Vector Search dedicado | Custo fixo de deployment sem justificativa de escala real agora — ver Abordagem B. | Reavaliar se o corpus crescer muito ou `VECTOR_SEARCH` nativo do BigQuery não performar. |
| UI/portal para o Q&A | Só API nesta fatia — mesmo padrão do `DEBTLAB_SIMULATOR` (engine+API primeiro, UI depois se pedida). | Fatia futura de Policy Lab/portal. |
| Novo rótulo formal em `ADR-028` para resposta de RAG | Decisão de nomenclatura/contrato, não de infraestrutura — não bloqueia o brainstorm, mas precisa ser resolvida no `/design` antes do `/build`. | `/design` desta mesma fatia (não adiado para depois, só não resolvido aqui). |

---

## 7. Requisitos-rascunho (para o `/define`)

- **R1.** Tabela nova em `br2036_gold` (nome a definir no `/design`, ex. `rag_methodology_notes`)
  com 1 linha por `metric_id` já real, parágrafo curto de metodologia + URL da fonte oficial como
  evidência — curadoria manual, versionada.
- **R2.** Conexão BigQuery↔Vertex AI (`google_bigquery_connection`, tipo `CLOUD_RESOURCE`) via
  Terraform, IAM least-privilege (`roles/aiplatform.user` só na service account da conexão) —
  infraestrutura nova, primeira vez no projeto.
- **R3.** Modelo remoto (`CREATE MODEL ... REMOTE WITH CONNECTION ... OPTIONS(ENDPOINT=
  'text-embedding-...')`) + coluna de embedding gerada via `ML.GENERATE_EMBEDDING` sobre o corpus
  (metodologia curada + `assumptions` de `metric_provenance` + descrição de `dataset_registry`).
- **R4.** Índice de busca híbrida: `VECTOR_SEARCH`/`CREATE VECTOR INDEX` (semântico) +
  `CREATE SEARCH INDEX`/`SEARCH()` (lexical/full-text) + filtros SQL por `metric_id`/organização/
  data (metadata) — decisão real sobre se um índice vetorial compensa no volume atual fica pro
  `/design`.
- **R5.** 1 endpoint novo (`POST /v1/knowledge/ask` ou equivalente, contrato exato a definir no
  `/design`) — recebe pergunta livre, retorna resposta + lista de citações (fonte real, URL,
  `metric_id` quando aplicável) + flag explícita quando a evidência é insuficiente (nunca
  fabrica), classe READ (`AGENTS.md`).
- **R6.** Nenhuma resposta pode citar uma URL/fonte que não exista de verdade em
  `metric_provenance`/`dataset_registry`/na tabela de metodologia curada — teste de regressão
  específico (mesmo espírito do "nenhum valor fabricado" já verificado em todo `/verify-spec`
  anterior).
- **R7.** Decisão de nomenclatura/contrato: como a resposta do RAG se classifica em relação a
  `ADR-028` (`observed`/`estimated`/`simulated`) — resolvida no `/design`, documentada (ADR novo
  ou nota em `ADR-028`).
- **R8.** Testes unitários da retrieval (dado sintético) + ≥1 integration test real contra
  BigQuery (mesmo padrão consolidado no hotfix do `MACRO_TWIN_EXPANSION` — `api/` já tem a
  convenção de teste de integração real, esta fatia reaproveita).
- **R9.** `SPEC-018-RAG.md` expandido (hoje 4 linhas) com o contrato real desta fatia — não um SPEC
  novo.
- **R10.** `docs/adrs/ADR-061-*.md` formalizando a decisão de arquitetura (BigQuery ML/nativo em
  vez de Vertex AI Vector Search dedicado), mesmo padrão do `ADR-059` (decisão de infra sem
  superar o ADR mais amplo que a antecede).

---

## 8. Decisões autônomas registradas

| Decisão | Motivo |
|---|---|
| Nome da feature: `RAG_PROVENANCE_QA`, não `RAG_BASICO` genérico | Reflete o corpus e o consumidor reais escolhidos (proveniência/metodologia das métricas), não uma descrição vaga de fase — mesmo padrão de nomear pelo valor de produto entregue, não pelo detalhe técnico interno, já usado em `DEBTLAB_SIMULATOR`. |
| Reaproveitar `SPEC-018-RAG.md` existente em vez de criar um SPEC novo | Já existe e já é o SPEC de RAG do projeto (mesmo padrão de reaproveitar `SPEC-009` no `DEBTLAB_SIMULATOR`). |
| Próximo ADR livre: `ADR-061` | Sequência confirmada por `ls docs/adrs/` — último é `ADR-060` (`MACRO_TWIN_EXPANSION`). |

---

## 9. Questões abertas (resolver no `/define` ou `/design`)

1. **Contagem exata de `metric_id`s reais hoje** — não suposta neste documento; `/design` confirma
   com uma query real contra `metric_provenance`/`dataset_registry` (mesmo padrão de nunca supor
   contagem sem inspecionar).
2. **`VECTOR_SEARCH` compensa no volume atual (corpus pequeno)?** — pode ser que full-text
   (`SEARCH()`) + filtros SQL já sejam suficientes pra 1ª fatia, com embedding/vetor como reforço
   não estritamente necessário no volume inicial. Decisão técnica real do `/design`, não deste
   documento.
3. **Rótulo/classificação da resposta do RAG em relação a `ADR-028`** — ver R7.
4. **Contrato exato do endpoint** (síncrono vs. streaming de resposta — `ADR-025`/SSE já existe
   pro progresso de agente, pode ser relevante aqui mesmo sem agente formal envolvido) — `/design`.
5. **Modelo de embedding exato** (`text-embedding-004`/`005`, ou equivalente Gemini mais recente
   disponível no Vertex AI no momento do `/design`) — confirmar disponibilidade real, não supor.

---

## 10. Domínios de KB para a Fase Define

- **PRDs:** nenhum PRD dedicado a RAG identificado ainda — `/define` confirma se `EPIC-024` tem
  PRD próprio ou se referencia um PRD mais amplo de Knowledge/Discovery.
- **SPECs:** `SPEC-018` (RAG, a expandir), `SPEC-019` (Graph/Ontology — referenciado, não
  implementado nesta fatia), `SPEC-007` (Provenance, corpus já real).
- **ADRs:** `ADR-026` (Hybrid RAG), `ADR-027` (GraphService — referenciado, não implementado),
  `ADR-012` (LLM nunca fabrica métrica oficial — aplica-se também a "nunca fabricar citação"),
  `ADR-028` (Observed/Estimated/Simulated — precisa de decisão sobre resposta de RAG), `ADR-002`
  (serverless-first — motivo de escolher BigQuery nativo em vez de Vertex AI Vector Search),
  `ADR-003` (BigQuery como verdade quantitativa).
- **Riscos:** `docs/risks/RISK-REGISTER.md`, `RISK-CONTROL-TEST-MATRIX.md` — checar se já existe
  algum controle mapeado para "resposta de IA deve citar fonte real"/"nunca fabricar" aplicável a
  RAG especificamente, ou se esta fatia precisa adicionar um novo.
- **Backlog:** `EPIC-024` (Knowledge/RAG, `STORY-024.01` a `.05`).
- **Precedente direto:** `ingestion/src/ingestion/provenance.py`/`registry.py` (schema real do
  corpus), `api/src/api/{main,bigquery_repo,config}.py` (padrão de endpoint a estender),
  `api/src/api/bigquery_repo.py::suggested_assumptions()` (precedente mais recente de query SQL
  real contra Gold, incluindo a lição do hotfix do `MACRO_TWIN_EXPANSION` sobre testar contra
  BigQuery real, não só mock).

---

## 11. Quality gate (Fase 0)

- [x] Mínimo de 3 perguntas de discovery feitas e respondidas (5 feitas)
- [x] Pergunta de amostras feita — corpus estruturado real confirmado disponível (parcial); texto
  de metodologia confirmado como gap real, não suposto
- [x] Pelo menos 2 abordagens exploradas com trade-offs (A, B, C)
- [x] Usuário confirmou explicitamente a abordagem escolhida (A) em múltiplos checkpoints
- [x] YAGNI aplicado — seção de itens removidos preenchida (7 itens)
- [x] Mínimo de 2 validações incrementais concluídas (checkpoint de consumidor unificado;
  checkpoint de confirmação final da leitura consolidada corpus+consumidor+arquitetura+texto)
- [x] Domínios de KB identificados para o Define
- [x] Requisitos-rascunho prontos para o `/define` (R1–R10)

---

## 12. Handoff

Pronto para `/define .claude/sdd/features/BRAINSTORM_RAG_PROVENANCE_QA.md`.
