# BRAINSTORM — MVP_WALKING_SKELETON

- **Feature:** MVP_WALKING_SKELETON
- **Status:** ✅ Complete (Defined)
- **Fase:** 0 (Brainstorm)
- **Criado:** 2026-09-03
- **Idioma:** PT-BR (alinhado a `docs/discovery/`)
- **Próximo passo:** `/define .claude/sdd/features/BRAINSTORM_MVP_WALKING_SKELETON.md`

---

## 1. Ideia

Definir e validar a **primeira fatia construível** do BRASIL 2036: um *walking skeleton*
vertical que prova a **cadeia de provenance ponta a ponta** — de um dataset aberto real
até um indicador canônico exibido, com objeto de provenance completo e o ritual de CI
todo verde.

O objetivo **não** é entregar um módulo; é provar cada elo de
`ARCHITECTURE.md` (`dados.gov.br → RAW → Bronze → Silver → Gold → métrica → apresentação`)
com o menor volume e a menor superfície possíveis, deixando o padrão pronto para os
datasets seguintes.

Isto é a única decisão de nível Fase 0 ainda em aberto: `CONTEXTO.md`, os 7 docs de
`docs/discovery/`, 18 PRDs, 32 SPECs e 50 ADRs já descrevem *o que* cada módulo é —
não fixam o ponto de partida concreto, o esqueleto de arquitetura, nem a ordem dos
primeiros PRs.

---

## 2. Contexto técnico

| Aspecto | Observação |
|---|---|
| Local no código | Repositório hoje é só documentação. A fatia cria as primeiras pastas de implementação (connector Python, SQL de transformação, Terraform, API, frontend mínimo). Estrutura a definir no `/design`. |
| Domínios de KB relevantes | `docs/prd/PRD-001` (Landing/Brasil Hoje), `PRD-002` (Open Data Hub); `docs/specs/SPEC-001` (GCP Foundation), `SPEC-002` (Open Data Discovery), `SPEC-003` (Resource Resolver/Connectors), `SPEC-004` (RAW/Bronze/Silver/Gold), `SPEC-005` (Data Contracts), `SPEC-006` (Data Trust Score), `SPEC-007` (Provenance), `SPEC-008` (Semantic Layer), `SPEC-026` (FastAPI/OpenAPI Client), `SPEC-031` (CI Gates); `docs/adrs/` ADR-001/002 (GCP serverless-first), ADR-003 (BigQuery = verdade quantitativa), ADR-005/006 (RAW imutável, camadas), ADR-007 (Dataform), ADR-011 (código IBGE de município/estado como chave territorial), ADR-012 (LLM nunca computa métrica oficial), ADR-028 (labels observed/estimated/simulated), ADR-039/040 (Terraform + WIF), ADR-041 (Landing é o produto da Fase 1), ADR-044 (portal público separado do autenticado). |
| Matriz de risco | `docs/risks/RISK-CONTROL-TEST-MATRIX.md` — leitura obrigatória no `/define`. |
| Padrões IaC | Terraform como fonte de mudança de infra (ADR-039); CI autentica por Workload Identity Federation, sem chave JSON de longa duração (ADR-040, SPEC-001); segredos em Secret Manager. |
| Fonte de dados da fatia | "Dívida Consolidada dos Estados e do DF", já identificada no Portal (`CONTEXTO.md §6`). Descoberta do recurso real (URL, schema, licença) é a **tarefa 1** — não há amostra ainda. |

---

## 3. Discovery

| # | Pergunta | Resposta | Impacto no desenho |
|---|---|---|---|
| 1 | Escopo: "todas as áreas" ou um tópico único? | Um brainstorm único: "primeira fatia construível / walking skeleton do MVP". | Documento único, foco em ordem de construção e esqueleto — não re-brainstorm dos módulos já especificados. |
| 2 | Qual o objetivo primário da fatia? | **Provar a cadeia de provenance ponta a ponta** (fatia vertical fina). | Descarta "infra primeiro" e "demo com stub". A fatia tem de tocar todos os elos com dado real. |
| 3 | Qual dataset? | **Dívida Consolidada dos Estados e do DF** (recomendação aceita; INSS era a 1ª escolha do usuário, revista por risco de ingestão). | Dataset pequeno, tabular, grão claro (`estado × reference_date × valor`), exercita a chave territorial (ADR-011), sem PII, alimenta M02 + M08, métrica reconhecível para card. |
| 4 | Onde roda? | **GCP real mínimo** — 1 projeto dev, Terraform só do que a fatia precisa, WIF para CI, BigQuery + Cloud Run reais. | Prova o elo BigQuery/deploy real sem bloquear na epic de Foundation inteira. Org/folders/multi-env ficam para o `SPEC-001` próprio. |
| 5 | O que é "pronto"? | **Ritual de CI todo verde**, nada burlado (`agent-eval` é N/A — sem agente). | Fatia inclui wiring de gates: format→lint→typecheck→unit→integration→data-contract→security→`terraform validate/plan`→spec-verifier. `/verify-spec` PASS por requisito. |
| 6 | Amostras disponíveis? | **Nenhuma.** | Descoberta e inspeção do recurso real no Portal é a primeira tarefa da fatia. |

---

## 4. Inventário de amostras

| Tipo | Disponível? | Uso previsto |
|---|---|---|
| Arquivos de entrada | Não | Obter na tarefa 1 (descoberta do recurso no dados.gov.br). |
| Exemplo de saída esperada | Não | Construir à mão no `/define`/`/design`: 1 linha Gold alvo + objeto de provenance, e 1 valor de DCL de referência para teste. |
| Ground truth | Não | Idem acima; um valor conhecido de um estado numa data serve de âncora de validação. |
| Código relacionado | Não | Sem trechos de connector/BigQuery/Terraform de outros projetos. Padrões vêm dos SPECs/ADRs. |

---

## 5. Abordagens exploradas

### Abordagem A — Fatia vertical única, num só encadeamento de PR
- **O quê:** discovery → Terraform mínimo → RAW→Bronze→Silver→Gold → provenance → API de métrica (FastAPI/Cloud Run) → card na Landing → CI, tudo junto.
- **Prós:** prova cada elo de uma vez; espelha `ARCHITECTURE.md`; deixa o padrão pronto para todo dataset futuro.
- **Contras:** primeiro PR gigante (Terraform + Python + SQL + API + frontend + CI); força decisões de stack de frontend, Dataform-vs-BQ-SQL e formato de API que merecem ADR/SPEC próprios.
- **Confiança:** 0.85 (docs alinham; sem precedente no código).

### Abordagem B — Coluna de dados primeiro (PR1), apresentação depois (PR2) ⭐ Escolhida
- **O quê:**
  - **PR1 — espinha de dados:** discovery + registro de 1 dataset + Terraform mínimo + RAW→Bronze→Silver→Gold + objeto de provenance, comprovado no BigQuery por query e por teste de data-contract. Sem API, sem frontend.
  - **PR2 — apresentação:** API de leitura de métrica + 1 card na Landing + deploy, sobre a Gold já provada.
- **Prós:** cada PR se revisa numa sentada; "provar a cadeia" fica quase todo satisfeito no PR1; a decisão de stack de frontend/API isola-se no PR2 com ADR próprio; menos risco por merge; casa com "mudanças pequenas e revisáveis" (`CLAUDE.md`).
- **Contras:** "ponta a ponta com card renderizado" só fecha no PR2; um pouco mais de cerimônia (1 SPEC com 2 ciclos de build, ou 2 SPECs).
- **Confiança:** 0.90.
- **Por que escolhida:** satisfaz o objetivo declarado (provar a cadeia), respeita a regra de PRs pequenos do projeto, e tira do caminho da fatia #1 as decisões de stack ainda não tomadas.

### Abordagem C — Fundação e contratos primeiro, a fatia anda sobre trilhos prontos
- **O quê:** `SPEC-001` + `SPEC-005` + `SPEC-007` + `SPEC-031` como incrementos próprios; só então a fatia da Dívida vira job pequeno.
- **Por que não escolhida:** é "infra primeiro", já descartado na Pergunta 2; tempo longo até algo vertical; risco de construir abstração de contrato/fundação sem consumidor que a valide (fere YAGNI).
- **Confiança:** 0.60.

---

## 6. Itens removidos / adiados (YAGNI)

| Item | Por que fora da fatia #1 | Vai para |
|---|---|---|
| Dataset INSS | Dois datasets na primeira fatia anulam o de-risking. Usuário sinalizou interesse ("INSS seria interessante"); mantido como co-igual **não**. | Fatia #2 — mesmo formato de pipeline, segundo domínio, volume maior com padrão já provado. |
| Foundation completa (org/folders, stg/prod, budgets, log sinks) | A fatia só precisa de 1 projeto dev e ~5 recursos. | `SPEC-001` próprio. |
| Dataform | Provar a cadeia não exige a ferramenta; SQL BigQuery puro resolve Silver/Gold da fatia. Arquivos ficam no formato Dataform (1 `.sql` por modelo). | Incremento seguinte levanta os `.sql` para o Dataform; ADR-007 honrado então (possível nota "vale a partir do incremento N+1"). |
| Data Trust Score (`SPEC-006`) | Score composto não é necessário para provar provenance. | Incremento pós-fatia. |
| Semantic Layer completo (`SPEC-008`) | A fatia define **uma** métrica canônica, não a camada. | `SPEC-008` próprio. |
| Séries históricas no card | Walking skeleton = **um valor atual** com provenance. | PRD-001 V1, depois da fatia. |
| Schema Drift Quarantine completo (`SPEC-005` inteiro) | A fatia leva só **um teste de data-contract** mínimo. | `SPEC-005` próprio. |
| Observabilidade/tracing full (`SPEC-025`) | É específico de agente; Cloud Run já dá logging/error reporting básico. | Quando entrar agente. |
| RAG / Copilot / agentes / auth / RBAC | Fora do escopo da fatia e da Landing pública (ADR-044). | Fases posteriores. |
| Gate `agent-eval` no CI | N/A — não há agente nesta fatia. | Ativa quando houver agente. |

---

## 7. Requisitos-rascunho (para o `/define`)

### PR1 — espinha de dados
- **R1.** Descobrir o recurso "Dívida Consolidada dos Estados e do DF" no dados.gov.br e registrar **1 linha** em `br2036_control.dataset_registry` com, no mínimo: `dataset_id`, `dataset_name`, `organization`, `source_url`, `resource_url`, `resource_format`, `license`, `br2036_domain='fiscal'`, `br2036_module='M02'`, `ingestion_status`, `active`.
- **R2.** Connector Python (Cloud Run Job) baixa o recurso e grava em **GCS RAW imutável**, com SHA-256 do conteúdo no nome do objeto e `ingested_at`. Nenhuma reescrita de objeto RAW existente.
- **R3.** Load **Bronze** (`br2036_bronze.debt_state_raw`): colunas de origem como texto + colunas técnicas `_source_uri`, `_ingested_at`, `_row_hash`.
- **R4.** **Silver** (`br2036_silver.debt_state`, SQL BigQuery): nome do ente → `state_ibge_code` via tabela de-para versionada; período → `reference_date` (DATE); valor → `NUMERIC`, unidade explícita `BRL`.
- **R5.** **Gold** (`br2036_gold.gold_debt_state_current`): `state_ibge_code`, `state_name`, `reference_date`, `metric_id='divida_consolidada_liquida'`, `value`, `unit='BRL'`.
- **R6.** **Provenance** (`br2036_gold.metric_provenance`, conforme `SPEC-007`): 1 linha por linha de métrica, com `value`, `unit`, `source`, `reference_date`, `model='none'`, `model_version`, `scenario='observed'`, `confidence`, `assumptions[]`.
- **R7.** **Terraform** (1 projeto dev): bucket GCS RAW, datasets BQ (`control`, `bronze`, `silver`, `gold`), Artifact Registry, Cloud Run Job, service account do job com least privilege, WIF pool para o CI. Sem stg/prod, sem org. `terraform validate/plan` sem exposição pública não declarada em ADR; sem chave estática no repo.
- **R8.** **Teste de data-contract** mínimo: schema esperado + `NOT NULL` em `state_ibge_code`, `reference_date`, `value`; `value >= 0`.
- **R9.** Prova de aceite: query mostrando Gold + `metric_provenance` coerentes para todos os estados numa `reference_date`; `/verify-spec` PASS por requisito.

### PR2 — apresentação
- **R10.** API FastAPI em Cloud Run: `GET /v1/metrics/{metric_id}` (com `?state_ibge_code=` opcional) devolve `value`, `unit`, `reference_date` **+ objeto `provenance` completo**. Pydantic → OpenAPI (ADR-024). Sem auth. Service account read-only sobre o dataset Gold.
- **R11.** Landing pública com **um card**: rótulo, valor formatado, `reference_date`, link "fonte" para o `source_url` real, marca visual de classe `observed` (ADR-028). O card consome a API — **nenhum número hard-coded** (ADR-012).
- **R12.** Deploy via Cloud Run; Terraform do PR2 estende o do PR1.
- **R13.** Testes: integração (API devolve `provenance` não-nulo); e2e leve (card renderiza o valor da API).
- **R14.** Ritual de CI todo verde; `/security-check` sem controle crítico ausente; `/verify-spec` PASS.

---

## 8. Decisões autônomas registradas

| Decisão | Motivo |
|---|---|
| Dataset = **Dívida Consolidada dos Estados e do DF**, não INSS Benefícios Emitidos | INSS é o domínio-carro-chefe mas o dataset P0 mais pesado (volume, encoding, dependente de glossário). Walking skeleton exige o dataset real mais leve que ainda exercite todos os elos. INSS vira fatia #2. |
| **SQL BigQuery puro** para Silver/Gold da fatia, arquivos no formato Dataform | Montar Dataform (conexão de repo, workspace, release config, CI) não tem retorno com 2 modelos e amplia a superfície da fatia. ADR-007 é honrado num incremento seguinte. |
| **GCP real mínimo**, não Foundation completa | Objetivo é provar a cadeia, não estabelecer a fundação. `SPEC-001` completo (org/folders/multi-env) vira incremento próprio. |
| Abordagem **B** (PR1 dados / PR2 apresentação) | Respeita "mudanças pequenas e revisáveis"; isola a decisão de stack de frontend/API; menor risco por merge. |

---

## 9. Questões abertas (resolver no `/define` ou `/design`, via ADR/SPEC quando alterarem arquitetura)

1. **Stack de frontend da Landing** — a fatia não fixa; exige apenas que o card consuma a API. Precisa de ADR (candidatos e critérios: build estático, acessibilidade/LCP dos SLOs de PRD-001, servível por Cloud Run).
2. **ADR-007 (Dataform)** — registrar formalmente que a transformação SQL da fatia #1 usa BigQuery SQL puro e que a migração para Dataform é um incremento seguinte (nota de amendment no ADR-007 ou ADR sucessor curto).
3. **Tabela de-para estado → `state_ibge_code`** — fonte e versionamento (IBGE); onde mora (`control`?).
4. **Um SPEC ou dois** — `SPEC` único cobrindo PR1+PR2 com dois ciclos de build, ou dois SPECs. Decisão do `/define`.
5. **`confidence` de valor observado** — convenção de preenchimento quando `scenario='observed'` (ex.: `1.0`) — alinhar com `SPEC-007`.
6. **Nomenclatura de projeto/datasets** — `gold_debt_state_current` vs. padrão de `CONTEXTO.md §10` (`gold_debt_trajectory`, `gold_state_profile`); confirmar convenção antes de criar.

---

## 10. Domínios de KB para a Fase Define

- **PRDs:** PRD-001 (Landing/Brasil Hoje), PRD-002 (Open Data Hub).
- **SPECs:** SPEC-001 (GCP Foundation), SPEC-002 (Open Data Discovery), SPEC-003 (Resource Resolver/Connectors), SPEC-004 (RAW/Bronze/Silver/Gold), SPEC-005 (Data Contracts), SPEC-007 (Provenance), SPEC-008 (Semantic Layer), SPEC-026 (FastAPI/OpenAPI Client), SPEC-031 (CI Gates).
- **ADRs:** ADR-001/002, ADR-003, ADR-005/006, ADR-007, ADR-011, ADR-012, ADR-028, ADR-039/040, ADR-041, ADR-044.
- **Riscos:** `docs/risks/RISK-CONTROL-TEST-MATRIX.md`, `docs/risks/RISK-REGISTER.md`.
- **Discovery:** `docs/discovery/07-MVP-BOUNDARIES.md`, `docs/discovery/05-ASSURANCE-MATRIX.md`, `docs/discovery/01-USER-JOURNEYS.md`.
- **Backlog:** EPIC-004 (Foundation), EPIC-005 (Open Data Hub), EPIC-006 (Data Platform), EPIC-007 (Data Governance), EPIC-009 (Fiscal & DebtLab), EPIC-033 (Public Portal).

---

## 11. Quality gate (Fase 0)

- [x] Mínimo de 3 perguntas de discovery feitas e respondidas (6 feitas)
- [x] Pergunta de amostras feita (inputs, outputs, ground truth)
- [x] Pelo menos 2 abordagens exploradas com trade-offs (A, B, C)
- [x] Usuário confirmou explicitamente a abordagem escolhida (B)
- [x] YAGNI aplicado — seção de itens removidos preenchida e confirmada
- [x] Mínimo de 2 validações incrementais concluídas (desenho PR1, desenho PR2)
- [x] Domínios de KB identificados para o Define
- [x] Requisitos-rascunho prontos para o `/define`

---

## 12. Handoff

Pronto para `/define .claude/sdd/features/BRAINSTORM_MVP_WALKING_SKELETON.md`.
