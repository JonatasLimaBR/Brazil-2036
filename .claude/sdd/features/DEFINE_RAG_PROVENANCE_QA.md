# DEFINE — RAG_PROVENANCE_QA

## Metadados

- **Feature:** RAG_PROVENANCE_QA
- **Status:** ✅ Complete (Built)
- **Fase:** 1 (Define)
- **Entrada:** `.claude/sdd/features/BRAINSTORM_RAG_PROVENANCE_QA.md` (Ready for Define)
- **Criado:** 2026-09-08
- **Idioma:** PT-BR
- **Clarity score:** 14/15 (HIGH)
- **Branch:** a criar — `feature/rag-provenance-qa`
- **Próximo passo:** `/design .claude/sdd/features/DEFINE_RAG_PROVENANCE_QA.md`

> Nota: assets do plugin SDD ausentes — documento segue a lista de seções obrigatórias do skill
> `sdd-define`, mesmo padrão das fatias anteriores.

---

## 1. Problem statement

O `EPIC-024 — Knowledge/RAG` (`SPEC-018`, `ADR-026`) está em 0% — nenhuma capability de RAG existe
no projeto. As 7 fatias de dado já shipadas deixaram `metric_provenance`/`dataset_registry` cheios
de URLs oficiais reais por métrica, mas hoje um usuário só vê "de onde veio o número" (a URL crua),
nunca "por que o número é calculado assim" em linguagem natural — não existe nenhuma forma de
perguntar isso ao sistema e receber uma resposta citando fonte real, sempre distinguível de uma
resposta fabricada.

---

## 2. Target users

| Persona | Descrição | Pain point |
|---|---|---|
| **Analista fiscal / macro** (primária, mesma persona de `MACRO_TWIN_EXPANSION`) | Quer entender a metodologia por trás de um número (dívida, fiscal, INSS, macro) sem sair do produto pra ler a página oficial da fonte | Hoje só vê a URL da fonte; precisa abrir e ler a página externa pra entender "por quê" |
| **Avaliador do concurso CGU** (secundária) | Julga sofisticação analítica e uso responsável de IA sobre dado aberto | Uma capability de Q&A que cita fonte real e nunca fabrica é diferencial direto de "AI responsável" (`ADR-012`), tema central de avaliação |

---

## 3. Goals (MoSCoW)

### MUST

- **G1.** Corpus real: `metric_provenance` (incluindo `assumptions`, já real) + `dataset_registry`
  (metadado estruturado) + parágrafos de metodologia curados manualmente, 1 por `metric_id` já
  real, cada um citando a URL oficial real como evidência.
- **G2.** Conexão BigQuery↔Vertex AI (`google_bigquery_connection`, `CLOUD_RESOURCE`) via
  Terraform, IAM least-privilege — infraestrutura nova, primeira vez no projeto.
- **G3.** Embeddings gerados via `ML.GENERATE_EMBEDDING` (modelo remoto) sobre o corpus.
- **G4.** Retrieval híbrida 100% dentro do BigQuery: `VECTOR_SEARCH`/`CREATE VECTOR INDEX`
  (semântico) + `CREATE SEARCH INDEX`/`SEARCH()` (lexical) + filtros SQL (metadata) — sem serviço
  gerenciado novo além da conexão IAM.
- **G5.** 1 endpoint novo de Q&A (`POST /v1/knowledge/ask` ou equivalente) — pergunta livre,
  resposta + citações reais (fonte/URL/`metric_id`), flag explícita de evidência insuficiente
  quando aplicável, classe READ.
- **G6.** Nenhuma resposta pode citar uma fonte que não exista de verdade no corpus indexado —
  teste de regressão dedicado.
- **G7.** `SPEC-018-RAG.md` expandido com o contrato real desta fatia (não SPEC novo).
- **G8.** Testes unitários da retrieval + ≥1 integration test real contra BigQuery.

### SHOULD

- **G9.** ADR novo (`ADR-061`) formalizando a decisão de arquitetura (BigQuery ML/nativo em vez de
  Vertex AI Vector Search dedicado), sem superar `ADR-026`.
- **G10.** Decisão de classificação da resposta do RAG em relação a `ADR-028`
  (`observed`/`estimated`/`simulated`) — resolvida e documentada no `/design`.

### COULD

- **G11.** `dataset_registry` indexado também por busca full-text (não só filtro exato) — útil pra
  "quais métricas de X existem" com sinônimos/variação de fraseado, mas não crítico pro Q&A de
  proveniência que é o caso de uso central.

---

## 4. Success criteria (mensuráveis)

| # | Critério | Medição |
|---|---|---|
| S1 | Endpoint de Q&A responde perguntas reais sobre proveniência/metodologia | `POST /v1/knowledge/ask` retorna resposta + citação real para ≥3 perguntas de teste sobre métricas já reais (dívida, fiscal, macro). |
| S2 | Zero citação fabricada | 100% das URLs/fontes citadas nas respostas de teste existem de verdade em `metric_provenance`/`dataset_registry`/tabela de metodologia. |
| S3 | Evidência insuficiente é reconhecida, não inventada | Para uma pergunta fora do corpus (ex.: sobre uma métrica que não existe), a resposta declara evidência insuficiente, não fabrica uma resposta plausível. |
| S4 | Infra nova provisionada corretamente | Conexão BigQuery↔Vertex AI + modelo remoto funcionando contra `brasil2036-dev` real, verificado ao vivo. |
| S5 | Testes cobrindo a retrieval | Unit tests + ≥1 integration test real PASS. |
| S6 | `/verify-spec` PASS | Verificação independente (sessão nova, read-only) = OVERALL PASS. |
| S7 | `ci-gate` verde | Todo PR desta fatia passa pelo `ci-gate` sem gate enfraquecido. |

---

## 5. Acceptance tests

- **AT1 — corpus indexado com embeddings reais.** *Given* o pipeline de indexação rodado contra
  `brasil2036-dev`, *When* inspeciono a tabela de metodologia/embeddings, *Then* cada `metric_id`
  já real tem 1 linha com parágrafo de metodologia + embedding gerado + URL de fonte real.
- **AT2 — pergunta sobre proveniência retorna resposta citando fonte real.** *Given* o corpus
  indexado, *When* chamo `POST /v1/knowledge/ask` com uma pergunta tipo "por que a dívida bruta do
  governo geral é calculada assim?", *Then* recebo uma resposta com citação(ões) cuja URL existe de
  verdade em `metric_provenance`/na tabela de metodologia.
- **AT3 — pergunta sobre catálogo retorna métricas reais.** *Given* o `dataset_registry` indexado,
  *When* pergunto "quais métricas de INSS existem?", *Then* a resposta lista `metric_id`s que
  existem de verdade no registry, não inventados.
- **AT4 — pergunta fora do corpus retorna evidência insuficiente.** *Given* uma pergunta sobre um
  tema fora do corpus indexado, *When* chamo o endpoint, *Then* a resposta declara explicitamente
  que a evidência é insuficiente, sem fabricar uma resposta plausível.
- **AT5 — nenhuma citação fabricada em nenhum teste.** *Given* qualquer resposta do endpoint nos
  testes AT2-AT4, *When* verifico cada URL/fonte citada contra o corpus real, *Then* 100% existem
  de verdade.
- **AT6 — infra nova funciona ao vivo.** *Given* o deploy em produção, *When* verifico a conexão
  BigQuery↔Vertex AI e o modelo remoto, *Then* `ML.GENERATE_EMBEDDING` executa sem erro contra
  `brasil2036-dev` real.
- **AT7 — ritual de CI completo.** *Given* qualquer PR desta fatia, *When* o CI roda, *Then*
  `ci-gate` resolve e bloqueia merge se qualquer gate falhar.

---

## 6. Out of scope

| Item | Motivo | Destino |
|---|---|---|
| `GraphService` completo (`ADR-027`, `EPIC-025`) | Q&A sobre proveniência plana não precisa de grafo de entidades/relações. | `EPIC-025`, fatia futura, se houver consumidor relacional real. |
| Parsing automático de HTML/PDF das páginas oficiais | Escopo de descoberta novo significativo; corpus desta fatia é curado manualmente. | Fatia futura de RAG, se a curadoria manual não escalar. |
| Documentos legais/fiscais novos (LOA/LDO/decretos/DOU/TCU) | Corpus desta fatia é só proveniência/metodologia das métricas já reais. | `EPIC-024`, fatia futura própria. |
| Chat multi-turn com memória de conversa | Endpoint é single-turn (pergunta → resposta com citação). | Fatia futura de portal/chat, se pedida. |
| Vertex AI Vector Search dedicado | Custo fixo de deployment sem justificativa de escala real agora. | Reavaliar se o corpus crescer muito ou `VECTOR_SEARCH` nativo não performar. |
| UI/portal para o Q&A | Só API nesta fatia, mesmo padrão do `DEBTLAB_SIMULATOR`. | Fatia futura de Policy Lab/portal. |

---

## 7. Constraints

- **C1.** Corpus desta fatia é só `metric_provenance`/`dataset_registry`/metodologia curada — nada
  de documento legal/fiscal novo nem documentação interna do projeto (`ADR-012`, decisão do
  usuário na descoberta).
- **C2.** Retrieval 100% dentro do BigQuery — sem serviço gerenciado novo além da conexão IAM
  BigQuery↔Vertex AI.
- **C3.** Toda resposta cita fonte real ou declara evidência insuficiente — nunca fabrica
  (`ADR-012`).
- **C4.** Endpoint é classe READ (`AGENTS.md`) — sem escrita em resposta a uma pergunta.
- **C5.** Todo merge em `main` é via PR (branch protection).
- **C6.** Reusa `ci-gate`/gates já existentes, sem enfraquecer.

---

## 8. Assumptions / risk register

| ID | Afirmação | Impacto se falsa | Validada |
|---|---|---|---|
| A1 | `ML.GENERATE_EMBEDDING`/`VECTOR_SEARCH`/`CREATE SEARCH INDEX` estão disponíveis na região do projeto (`southamerica-east1`) sem pré-requisito de quota/allowlist bloqueante | Pode exigir mudar de região pro dataset de RAG ou usar uma região multi-region — escopo de `/design` | ☐ |
| A2 | O volume do corpus inicial (poucas dezenas de linhas) ainda se beneficia de `VECTOR_SEARCH`/índice vetorial vs. só `SEARCH()` full-text | Se não compensar, `/design` pode decidir adiar o índice vetorial pra quando o corpus crescer, usando só full-text + filtros na v1 | ☐ |
| A3 | O modelo de embedding remoto (`text-embedding-...`) e o modelo generativo (Gemini) para compor a resposta final estão ambos disponíveis via Vertex AI no momento do `/design`, sem custo/quota surpresa | Impacto no desenho da conexão/modelo remoto; `/design` confirma com inspeção real, não suposição | ☐ |
| A4 | Contagem exata de `metric_id`s reais hoje (aprox. 11-13: dívida, fiscal ×3, INSS ×2-3, macro ×5) é suficiente pra provar o padrão de retrieval híbrida com significância | Se muito pequena, os testes de qualidade de retrieval (AT2/AT3) ficam mais fracos — mitigado por usar perguntas de teste bem definidas, não amostragem estatística | ☐ |

---

## 9. Technical context

| Aspecto | Definição |
|---|---|
| **Onde vive** | Tabela de metodologia curada + colunas de embedding em `br2036_gold` (nome exato a definir no `/design`); `infra/terraform/` (+conexão BigQuery↔Vertex AI, IAM); `api/src/api/{main,bigquery_repo,config}.py` (+1 endpoint novo); `docs/adrs/` (+`ADR-061`); `docs/specs/SPEC-018-RAG.md` (expandido). |
| **Impacto IaC** | **Sim, pela 1ª vez em RAG:** `google_bigquery_connection` novo (`CLOUD_RESOURCE`) + IAM (`roles/aiplatform.user` escopado à service account da conexão, least-privilege). Sem serviço Cloud Run/GKE novo. |
| **Domínios de KB** | `SPEC-018` (RAG, a expandir), `ADR-026` (Hybrid RAG), `ADR-012` (nunca fabricar), `ADR-028` (classificação de dado, precisa de decisão nova pra resposta de RAG), `ADR-002`/`ADR-003` (serverless-first, BigQuery como verdade quantitativa — motivam a escolha de arquitetura). |

---

## 10. Clarity score breakdown

| Elemento | Nota | Máx | Observação |
|---|---|---|---|
| Problem | 3 | 3 | Gap concreto e verificado: `EPIC-024` em 0%, corpus real já existe mas sem texto explicativo nem forma de perguntar. |
| Users | 3 | 3 | Persona primária e secundária bem definidas, ambas já usadas em fatias anteriores, com pain point específico e novo (não repete pain point de nenhuma fatia anterior). |
| Goals | 3 | 3 | 8 MUST, 2 SHOULD, 1 COULD; todos mensuráveis e rastreáveis à descoberta do brainstorm, incluindo infra nova (G2/G3/G4) explicitada. |
| Success | 3 | 3 | S1-S7 com critérios verificáveis, incluindo "zero citação fabricada" como critério explícito e testável. |
| Scope | 2 | 3 | Out-of-scope bem povoado (6 itens), mas 4 assumptions reais (A1-A4) não validadas — disponibilidade real de `ML.GENERATE_EMBEDDING`/`VECTOR_SEARCH` na região do projeto e se o índice vetorial compensa no volume atual são incertezas técnicas genuínas, só resolvidas no `/design`. |
| **Total** | **14** | **15** | **HIGH — prosseguir para `/design`.** |

---

## 11. Open questions

| ID | Questão | Resolver em |
|---|---|---|
| OQ1 | Contagem exata de `metric_id`s reais hoje | `/design`, query real |
| OQ2 | `VECTOR_SEARCH`/índice vetorial compensa no volume atual, ou só full-text+filtros basta pra v1? | `/design` |
| OQ3 | Disponibilidade real de `ML.GENERATE_EMBEDDING`/`VECTOR_SEARCH`/`CREATE SEARCH INDEX` em `southamerica-east1` | `/design`, descoberta real |
| OQ4 | Classificação da resposta do RAG em relação a `ADR-028` | `/design` |
| OQ5 | Contrato exato do endpoint (síncrono vs. streaming/SSE) | `/design` |
| OQ6 | Modelo de embedding e modelo generativo exatos disponíveis no momento | `/design`, descoberta real |

---

## 12. Revision history

| Data | Versão | Mudança | Autor |
|---|---|---|---|
| 2026-09-08 | 1.0 | Criação a partir de `BRAINSTORM_RAG_PROVENANCE_QA.md`. Clarity 14/15. Status → Ready for Design. | /define (Claude Sonnet 5) |
