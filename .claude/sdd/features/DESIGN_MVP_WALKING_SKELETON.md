# DESIGN — MVP_WALKING_SKELETON

## Metadados

- **Feature:** MVP_WALKING_SKELETON
- **Status:** Ready for Build
- **Fase:** 2 (Design)
- **Entrada:** `.claude/sdd/features/DEFINE_MVP_WALKING_SKELETON.md` (Clarity 14/15)
- **Criado:** 2026-09-03
- **Idioma:** PT-BR
- **Confiança de design:** 0.82 — padrões vêm de SPECs/ADRs do repo (não há `${CLAUDE_PLUGIN_ROOT}/kb/`); agentes casados a partir da lista disponível na sessão.
- **Próximo passo:** `/build .claude/sdd/features/DESIGN_MVP_WALKING_SKELETON.md`

> Nota de ambiente: assets do plugin SDD ausentes (`DESIGN_TEMPLATE.md`, `kb/`, `agents/**`,
> `tools/spec-linter`). O documento segue a lista de seções do skill `sdd-design`. O **contract
> gate (`spec-lint`) não pôde ser executado** — validar manualmente quando o plugin existir.

---

## 1. Grounding (KB / SPEC / ADR)

| Fonte | O que fixa para este design |
|---|---|
| `SPEC-002` | Discovery guarda `run_id`, timestamps, counts, errors; **não** auto-promove dataset. |
| `SPEC-003` | Interface de connector: `discover, metadata, download, validate, checkpoint`. Retries limitados e registrados. Checkpoint evita recarga quando hash do recurso não mudou. Tipos iniciais: CSV, JSON, ZIP, XLSX, REST, CKAN/OData. |
| `SPEC-004` | RAW imutável = bytes de origem **+ manifest**. Bronze = formato da origem. Silver = tipos/datas/**chaves territoriais**/code sets. Gold = produtos canônicos. **Drift que quebra schema é posto em quarentena antes da Silver.** |
| `SPEC-005` | Campos do contrato: dataset/version/keys/required fields/types/null thresholds/freshness/quality rules/evolution policy. Violação que quebra **para a promoção + gera alerta**. Versão imutável após release. |
| `SPEC-007` | Provenance resolve `metric → Gold → Silver transform → Bronze → source resource → catalog dataset → org`. **API: `GET /v1/provenance/{metric_id}`**; resposta traz source URLs, reference date, transform versions, trust status. |
| `SPEC-026` / `ADR-024` | FastAPI/Pydantic definem contrato. **OpenAPI gerado no CI. Cliente TS gerado do OpenAPI; frontend não copia DTO à mão.** Passo de geração vira dependência de CI. |
| `SPEC-031` | Checks obrigatórios: format/lint/typecheck, unit, integration, contracts, security, Terraform validation, agent evals **quando afetados**, spec verification. Substituto "warning-only" não vale para gate crítico. |
| `SPEC-032` | `main` protegida, PR-only, CODEOWNERS em caminhos sensíveis, Conventional Commits, PR liga problema/PRD/SPEC/ADR/risco/evidência de teste. |
| `ADR-005` | RAW = object storage imutável; nunca sobrescreve; lifecycle policy gerencia crescimento. |
| `ADR-007` | Dataform é a decisão para transformação SQL. **Amendment necessário** para "SQL puro na fatia #1" — ver Decisão D2. |
| `ADR-011` | Chave territorial = **código IBGE** canônico + surrogate opcional. Precisa de mapa para mudanças/exceções históricas. |
| `ADR-028` | Classificação **tipada** `observed/estimated/simulated` em **dados + API + UI** — não disclaimer textual. |
| `ADR-044` | Design system compartilhado com superfícies pública/autenticada separadas. Fatia #1 = só superfície pública. |
| `RISK-CONTROL-TEST-MATRIX` | Linhas relevantes: **R-003** typed OBSERVED → `test_output_classification`; **R-006** Data Contract + quarantine → `contract_test_breaking_drift`; **R-008** freshness + source health → `test_stale_source_block`; **R-011** secret scan → `secret_scan`; **R-012** budgets → `cost_guardrail_test`. |

Confiança pela matriz do skill: **KB patterns ausentes / agent match encontrado → 0.80**, elevado a **0.82** por SPECs/ADRs do repo cobrirem bem os padrões.

---

## 2. Arquitetura

### 2.1 Visão geral

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                         MVP WALKING SKELETON — dev project                     │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  dados.gov.br                                                                  │
│  (recurso "Dívida Consolidada dos Estados e do DF")                            │
│        │  discover / metadata / download (SPEC-003)                            │
│        ▼                                                                       │
│  ┌───────────────────────── UNIDADE 1: ingestion job ───────────────────────┐  │
│  │  Cloud Run Job (Python)   [PR1]                                          │  │
│  │                                                                          │  │
│  │  registry.upsert ─▶ connector.download ─▶ raw.write ─▶ bronze.load       │  │
│  │       │                                    │ (GCS, hash no nome,          │  │
│  │       │                                    │  + manifest, no-overwrite)   │  │
│  │       ▼                                    ▼                              │  │
│  │  br2036_control          GCS gs://…-raw/    br2036_bronze.debt_state_raw   │  │
│  │  .dataset_registry                                 │                      │  │
│  │  .ref_estado_ibge                                  ▼                      │  │
│  │                              contract.check(bronze)  ◀── contract v1      │  │
│  │                              (quarentena antes da Silver, SPEC-004/005)   │  │
│  │                                                   │ pass                  │  │
│  │                                                   ▼                       │  │
│  │                         silver.sql ─▶ br2036_silver.debt_state            │  │
│  │                                                   │                       │  │
│  │                         gold.sql   ─▶ br2036_gold.gold_debt_state_current │  │
│  │                                                   │                       │  │
│  │                         provenance.write ─▶ br2036_gold.metric_provenance │  │
│  │                                                   │                       │  │
│  │                              contract.check(gold)  (S1/S2)                 │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                   │ BigQuery (verdade quant.)  │
│        ┌──────────────────────────────────────────┴───────────────┐            │
│        ▼                                                          ▼            │
│  ┌──────────── UNIDADE 2: metric API ───────────┐        (leitura read-only)   │
│  │  Cloud Run Service (FastAPI/Pydantic)  [PR2] │                              │
│  │  GET /v1/metrics/{metric_id}                 │                              │
│  │  GET /v1/provenance/{metric_id}  (SPEC-007)  │                              │
│  │  GET /openapi.json  ──▶ gerado no CI ──▶ cliente TS                        │
│  └───────────────┬─────────────────────────────┘                              │
│                  │ HTTP (JSON)                                                 │
│                  ▼                                                             │
│  ┌──────────── UNIDADE 3: web ──────────────────┐                             │
│  │  Cloud Run Service (Vite + TS, build estático)  [PR2]                     │  │
│  │  1 card: valor · reference_date · link "fonte" · selo `observed`          │  │
│  │  usa cliente TS gerado (ADR-024) — sem número no bundle (ADR-012)         │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                               │
│  Terraform  [PR1 cria job+infra de dados; PR2 adiciona os 2 services]          │
│  WIF pool ◀── GitHub Actions (sem chave estática, ADR-040)                     │
│  Budget + billing export (R-012)                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Componentes

| # | Componente | Unidade | Tecnologia | Propósito |
|---|---|---|---|---|
| C1 | `connectors/divida_estados` | 1 | Python 3.12 | Implementa a interface `SPEC-003` para o recurso da Dívida Consolidada. |
| C2 | `raw` | 1 | Python + GCS client | Grava bytes de origem em `gs://<proj>-raw/divida_estados/<sha256>.<ext>` + `<sha256>.manifest.json`; `if_generation_match=0` (nunca sobrescreve). |
| C3 | `bronze` | 1 | Python + `bq load` | Carrega RAW → `br2036_bronze.debt_state_raw` (colunas STRING + `_source_uri`, `_ingested_at`, `_row_hash`). |
| C4 | `contract` | 1 | Python + YAML | Lê `contracts/divida_consolidada_estados.yaml` (v1); valida schema/keys/nulls/freshness em 2 pontos: **Bronze→Silver** (quarentena) e **Gold** (aceite). |
| C5 | `sql/silver/debt_state.sql` | 1 | BigQuery SQL (formato Dataform) | Ente → `state_ibge_code` via `ref_estado_ibge`; período → `reference_date DATE`; valor → `NUMERIC` BRL. Ente não mapeado ⇒ 0 linhas + erro. |
| C6 | `sql/gold/gold_debt_state_current.sql` | 1 | BigQuery SQL (formato Dataform) | `MERGE` idempotente por `(state_ibge_code, reference_date)`; `metric_id='divida_consolidada_liquida'`, `unit='BRL'`, `data_class='observed'`. |
| C7 | `provenance` | 1 | Python + BigQuery | Escreve `br2036_gold.metric_provenance` (1 linha por métrica, campos `SPEC-007`, `scenario='observed'`, `model='none'`, `confidence=1.0`). |
| C8 | `registry` | 1 | Python + BigQuery | Upsert de 1 linha em `br2036_control.dataset_registry`; carga de `ref_estado_ibge` a partir de `reference/estado_ibge.csv`. |
| C9 | `pipeline` | 1 | Python | Orquestra C8→C1→C2→C3→C4(bronze)→C5→C6→C7→C4(gold); `run_id`, timestamps, counts, errors (SPEC-002). |
| C10 | `api` | 2 | FastAPI + Pydantic v2 | `GET /v1/metrics/{metric_id}`, `GET /v1/provenance/{metric_id}`, `/openapi.json`. Read-only sobre `br2036_gold`. |
| C11 | `api/bigquery_repo` | 2 | BigQuery client | Query da Gold (última `reference_date`) e de `metric_provenance`; resolve a cadeia `SPEC-007`. |
| C12 | `web` | 3 | Vite + TypeScript (vanilla), CSS | 1 card; `fetch` via cliente TS gerado; selo visual por `data_class` (ADR-028); link "fonte" para `source_url`. |
| C13 | `web/api-client/` | 3 | Gerado (openapi-typescript) | DTOs + fetch tipado a partir de `openapi.json`. **Não editar à mão** (ADR-024). |
| C14 | `infra/terraform` | — | Terraform + Google provider | 1 projeto dev: bucket RAW (+versioning+lifecycle), datasets `control/bronze/silver/gold`, Artifact Registry, Cloud Run Job (PR1) + 2 Services (PR2), service accounts least-priv, WIF pool/provider, budget. Backend de state em GCS. |
| C15 | `.github/workflows` | — | GitHub Actions | `data.yml` (PR1), `api-web.yml` (PR2), `security.yml` (secret scan). Auth por WIF. |

### 2.3 Fluxo de dados

1. `pipeline` gera `run_id`; `registry` garante a linha do dataset e a tabela `ref_estado_ibge`.
2. `connector.discover/metadata` resolvem `resource_url` e `resource_hash`; se o hash == último checkpoint, o job encerra com "no-op" (SPEC-003).
3. `connector.download` baixa os bytes; `raw.write` grava `<sha256>.<ext>` + `<sha256>.manifest.json` (source_uri, fetched_at, http_status, bytes, content_sha256). Objeto existente ⇒ não reescreve.
4. `bronze.load` cria/append em `debt_state_raw` com colunas técnicas.
5. `contract.check(bronze)`: schema/keys esperados. Falha ⇒ **para antes da Silver**, marca quarentena, exit ≠ 0, alerta (log estruturado). (SPEC-004/005, R-006.)
6. `silver.sql` normaliza para `debt_state`. Ente sem correspondência em `ref_estado_ibge` ⇒ falha explícita.
7. `gold.sql` faz `MERGE` em `gold_debt_state_current`.
8. `provenance.write` insere/atualiza `metric_provenance` para cada linha de métrica da `reference_date` corrente.
9. `contract.check(gold)`: 28 linhas para a `reference_date`, `NOT NULL` em PK, `value >= 0`, cobertura de provenance 100%. Falha ⇒ exit ≠ 0.
10. API lê `gold_debt_state_current` (`WHERE reference_date = (SELECT MAX(...))`) e `metric_provenance`. Web renderiza.

### 2.4 Pontos de integração externos

| Dependência | Uso | Tratamento de falha |
|---|---|---|
| dados.gov.br (recurso de arquivo) | download na ingestão | retries limitados e registrados (SPEC-003); falha ⇒ job falha, nada promovido |
| GCP: GCS, BigQuery, Cloud Run, Artifact Registry, IAM, Cloud Billing | infra + runtime | Terraform `plan` no CI; budget + alerta (R-012) |
| IBGE (tabela de UFs) | semente de `reference/estado_ibge.csv` (offline, versionada) | sem dependência em runtime |
| GitHub Actions OIDC ↔ GCP WIF | auth de CI | provider WIF restrito a repo/branch; sem chave estática (ADR-040) |

---

## 3. Decisões (ADRs inline)

### D1 — Duas unidades implantáveis, entregues em duas PRs

| Atributo | Valor |
|---|---|
| Status | Accepted |
| Data | 2026-09-03 |

**Contexto:** A fatia toca Terraform, Python de ingestão, SQL, API e frontend. Um único PR com tudo é irrevisável e força, no mesmo diff, decisões de stack que merecem ADR próprio. `CLAUDE.md` exige "mudanças pequenas e revisáveis".

**Escolha:** **PR1 = espinha de dados** (infra de dados + ingestion job + contrato + gates de dados no CI), comprovada por query no BigQuery. **PR2 = apresentação** (API + geração OpenAPI/cliente TS + card + 2 Cloud Run Services + e2e + deploy). Três unidades implantáveis (job, api, web) sem código compartilhado; o único cruzamento é o artefato `openapi.json → cliente TS`, gerado no CI (padrão ADR-024).

**Racional:** isola risco por merge; o objetivo "provar a cadeia de provenance" fica ~90% satisfeito já no PR1; a decisão de stack de frontend fica contida no PR2; cada PR liga-se a um conjunto menor de ATs.

**Alternativas rejeitadas:**
1. *PR único vertical* — rejeitado: diff grande, revisão fraca, acopla decisões independentes.
2. *Fundação + contratos primeiro, fatia depois* (Abordagem C do BRAINSTORM) — rejeitado: contradiz o objetivo da Fase 0 (provar a cadeia, não estabelecer a fundação) e adia qualquer coisa vertical.

**Consequências:**
- (+) revisão barata; rollback por unidade; padrão replicável na fatia #2.
- (−) "ponta a ponta com card renderizado" só fecha no PR2; um SPEC com dois ciclos de build (ver D6).

### D2 — BigQuery SQL puro na fatia #1; formato Dataform; ADR-007 via amendment

| Atributo | Valor |
|---|---|
| Status | Accepted (requer nota de amendment no ADR-007) |
| Data | 2026-09-03 |

**Contexto:** ADR-007 fixa **Dataform** para transformação SQL. Levantar Dataform (conexão de repo, workspace, release config, wiring no CI) não tem retorno com 2 modelos e amplia a superfície do PR1, contra o objetivo de fatia mínima.

**Escolha:** Silver/Gold como arquivos `.sql` **no formato Dataform** (um `.sql` por modelo, sem glue procedural, nomes de tabela parametrizados por `config.yaml`), executados na fatia #1 via cliente BigQuery do job. Um **incremento seguinte** cria o projeto Dataform e adota os mesmos `.sql` sem reescrita. Registrar no ADR-007 uma nota: *"vale a partir do incremento N+1; a fatia MVP_WALKING_SKELETON usa BigQuery SQL direto, arquivos já no formato Dataform"*.

**Racional:** honra a intenção do ADR-007 (formato e reprodutibilidade) sem pagar o custo de setup antes de haver consumo que o justifique (YAGNI); migração posterior é mecânica.

**Alternativas rejeitadas:**
1. *Dataform já na fatia #1* — rejeitado: PR1 cresce, sem payoff com 2 modelos.
2. *SQL embutido em strings Python* — rejeitado: perde testabilidade e o caminho de migração para Dataform.

**Consequências:**
- (+) PR1 menor; caminho de migração barato.
- (−) ADR-007 precisa de amendment explícito antes do merge do PR1 (senão fere "nunca contrariar ADR silenciosamente").

### D3 — Dois endpoints: `/v1/metrics/{id}` e `/v1/provenance/{metric_id}`

| Atributo | Valor |
|---|---|
| Status | Accepted |
| Data | 2026-09-03 |

**Contexto:** o DEFINE previa `GET /v1/metrics/{metric_id}` devolvendo valor + provenance embutido. `SPEC-007` **exige** `GET /v1/provenance/{metric_id}` como resolvedor da cadeia completa (source URLs, reference date, transform versions, trust status).

**Escolha:** expor **ambos**. `/v1/metrics/{metric_id}` (com `?state_ibge_code=` opcional) devolve `value`, `unit`, `reference_date`, `data_class` (`observed|estimated|simulated`, ADR-028) e um `provenance` **resumido** (source, reference_date, trust_status). `/v1/provenance/{metric_id}` devolve o objeto completo do `SPEC-007`.

**Racional:** o card precisa de uma chamada só (métrica + resumo de fonte); auditoria/entidades a jusante precisam do resolvedor canônico. Conformidade literal com `SPEC-007`.

**Alternativas rejeitadas:**
1. *Só `/v1/metrics`* — rejeitado: viola `SPEC-007`.
2. *Só `/v1/provenance`* — rejeitado: card faria 2 chamadas e recomporia a métrica no cliente.

**Consequências:** (+) conforme SPEC-007; (−) dois modelos Pydantic e dois testes de endpoint.

### D4 — Checagem de contrato no limite Bronze→Silver (quarentena) além da Gold

| Atributo | Valor |
|---|---|
| Status | Accepted |
| Data | 2026-09-03 |

**Contexto:** o DEFINE pedia "um teste de data-contract sobre a Gold". `SPEC-004` determina que **drift que quebra schema seja posto em quarentena antes da Silver**.

**Escolha:** `contract.check` roda em **dois pontos** — (a) após `bronze.load`, valida schema/keys de origem contra o contrato v1; falha ⇒ nada entra na Silver, estado `quarantined`, exit ≠ 0, alerta; (b) após `gold.sql`, valida completude/nulos/`value>=0`/cobertura de provenance.

**Racional:** conformidade com `SPEC-004`/`SPEC-005` e com R-006 (`contract_test_breaking_drift`). O custo é um segundo ponto de checagem sobre o mesmo YAML — baixo.

**Alternativas rejeitadas:**
1. *Só na Gold* — rejeitado: drift de origem contaminaria a Silver antes de ser detectado.

**Consequências:** (+) drift barrado cedo; (−) o `pipeline` ganha um ramo de quarentena e um teste a mais (`contract_test_breaking_drift`).

### D5 — Frontend: Vite + TypeScript vanilla, build estático em Cloud Run (resolve OQ1)

| Atributo | Valor |
|---|---|
| Status | Accepted |
| Data | 2026-09-03 |

**Contexto:** OQ1 do DEFINE. Restrições: build estático, LCP/acessibilidade nos SLOs de PRD-001, servível por Cloud Run, **deve** consumir cliente TS gerado do OpenAPI (`SPEC-026`/ADR-024). O card faz `fetch` em runtime (número não pode estar no bundle — ADR-012/AT10).

**Escolha:** **Vite + TypeScript sem framework**. Saída estática (`vite build`), servida por imagem mínima (`nginx:alpine` ou `caddy`) no Cloud Run. Cliente gerado com `openapi-typescript` em `web/api-client/`. Acessibilidade tratada no markup do card (`a11y-architect`).

**Racional:** menor superfície e menor JS possível para um card único ⇒ melhor LCP; sem custo de framework/SSR; ainda TypeScript, então o cliente gerado é idiomático. Alinha com ADR-044 (superfície pública simples).

**Alternativas rejeitadas:**
1. *Astro* — bom para conteúdo estático, mas adiciona toolchain/ilhas para um único fetch; reconsiderar quando a Landing tiver muitas seções (PRD-001 V1).
2. *Next.js* — SSR/BFF e superfície grande demais para a fatia; possível reavaliação na fase de Portais.
3. *HTML + JS puro sem build* — rejeitado: quebra a geração/consumo tipado do cliente (`SPEC-026`).

**Consequências:**
- (+) bundle mínimo; build reprodutível; caminho claro de evolução.
- (−) quando a Landing crescer, provável migração para Astro/Next — troca contida no `web/`.
- Marca um **ADR novo (ADR-051)** a ser criado no build.

### Questões abertas resolvidas (menores)

| OQ | Resolução |
|---|---|
| OQ2 | Ver D2 — nota de amendment no ADR-007 é entregável do PR1. |
| OQ3 | de-para = `ingestion/reference/estado_ibge.csv` (28 linhas, semeado da tabela de UFs do IBGE, versionado no repo) → carregado em `br2036_control.ref_estado_ibge` por `registry`. |
| OQ4 | Ver D6 — **um** SPEC (`SPEC-033`), dois ciclos de build. |
| OQ5 | `confidence = 1.0` quando `scenario='observed'` nesta fatia; propor a convenção como nota em `SPEC-007`. |
| OQ6 | Usar `br2036_gold.gold_debt_state_current` (nome específico e novo). Relacionar com `gold_debt_trajectory` / `gold_state_profile` do `CONTEXTO §10` fica como trabalho futuro registrado no `SPEC-033`. |
| OQ7 | Gatilho = **manual** (`gcloud run jobs execute`) na fatia #1. Cloud Scheduler é COULD (G11). |
| OQ8 | Card mostra `MAX(reference_date)` presente na Gold. |

### D6 — Um SPEC único cobrindo PR1+PR2

| Atributo | Valor |
|---|---|
| Status | Accepted |
| Data | 2026-09-03 |

**Contexto:** OQ4. A fatia é uma capacidade só (provar a cadeia); dividir em dois SPECs duplicaria contexto e critérios de aceite.

**Escolha:** criar **`docs/specs/SPEC-033-MVP-WALKING-SKELETON.md`** com duas seções de entrega (PR1, PR2) e a matriz de requisitos R1–R14 do DEFINE. `/verify-spec` roda por PR contra o subconjunto aplicável.

**Racional:** um contrato, uma rastreabilidade; alinha com `SPEC-032` (PR liga a um SPEC).

**Alternativas rejeitadas:** *dois SPECs* — rejeitado: overhead sem ganho para uma capacidade única.

**Consequências:** (+) rastreabilidade simples; (−) o SPEC precisa marcar claramente qual requisito pertence a qual PR.

---

## 4. Manifesto de arquivos (agent matching)

Agentes casados a partir da lista disponível na sessão (não há `${CLAUDE_PLUGIN_ROOT}/agents/**`). Regra: tipo de arquivo (alto), palavras-chave de propósito (alto), caminho (médio), domínio (médio), fallback `(general)` (baixo).

### PR1 — espinha de dados

| # | Arquivo | Ação | Propósito | Agente | Deps |
|---|---|---|---|---|---|
| 1 | `docs/adrs/ADR-051-frontend-stack-vite-ts.md` | Create | Registrar D5 | `architect` | — |
| 2 | `docs/adrs/ADR-007-...` (amendment) | Modify | Nota "Dataform a partir do incremento N+1" (D2) | `architect` | — |
| 3 | `docs/specs/SPEC-033-MVP-WALKING-SKELETON.md` | Create | Contrato da fatia, R1–R14, split PR1/PR2 (D6) | `architect` | 1,2 |
| 4 | `infra/terraform/providers.tf` `backend.tf` `variables.tf` `outputs.tf` | Create | Provider Google, state em GCS, variáveis do projeto dev | `gcp-data-architect` | — |
| 5 | `infra/terraform/storage.tf` | Create | Bucket RAW + versioning + lifecycle (ADR-005) | `gcp-data-architect` | 4 |
| 6 | `infra/terraform/bigquery.tf` | Create | Datasets `control/bronze/silver/gold` | `gcp-data-architect` | 4 |
| 7 | `infra/terraform/artifact_registry.tf` | Create | Repo de imagens do job | `gcp-data-architect` | 4 |
| 8 | `infra/terraform/cloud_run.tf` | Create | Cloud Run **Job** (connector) | `gcp-data-architect` | 6,7 |
| 9 | `infra/terraform/iam.tf` | Create | Service accounts least-priv (job: `bigquery.jobUser` + `dataEditor` nos datasets, `storage.objectCreator` no bucket) | `ci-cd-specialist` | 4 |
| 10 | `infra/terraform/wif.tf` | Create | Workload Identity pool/provider restrito a repo+branch (ADR-040) | `ci-cd-specialist` | 4 |
| 11 | `infra/terraform/budget.tf` | Create | Budget + alerta no projeto dev (R-012) | `ci-cd-specialist` | 4 |
| 12 | `ingestion/pyproject.toml` `Dockerfile` | Create | Pacote Python + imagem do job | `python-developer` | — |
| 13 | `ingestion/src/ingestion/config.yaml` | Create | dataset_id, URLs, nomes de tabela, project, dataset de RAW | `(general)` | — |
| 14 | `ingestion/src/ingestion/connectors/base.py` | Create | Interface `SPEC-003` (`discover/metadata/download/validate/checkpoint`) + retries limitados | `ai-data-engineer-gcp` | 12 |
| 15 | `ingestion/src/ingestion/connectors/divida_estados.py` | Create | Connector concreto (CSV/XLSX) do recurso da Dívida | `ai-data-engineer-gcp` | 14 |
| 16 | `ingestion/src/ingestion/raw.py` | Create | Escrita GCS RAW: `<sha256>.<ext>` + `.manifest.json`, `if_generation_match=0` | `ai-data-engineer-gcp` | 12,13 |
| 17 | `ingestion/src/ingestion/bronze.py` | Create | `bq load` → `debt_state_raw` + colunas técnicas | `ai-data-engineer-gcp` | 16 |
| 18 | `ingestion/src/ingestion/registry.py` | Create | Upsert `dataset_registry`; carga de `ref_estado_ibge` | `python-developer` | 13 |
| 19 | `ingestion/reference/estado_ibge.csv` | Create | de-para 28 linhas UF→código IBGE (OQ3) | `(general)` | — |
| 20 | `ingestion/contracts/divida_consolidada_estados.yaml` | Create | Contrato v1 (`SPEC-005`: keys, types, null thresholds, freshness, evolution) | `data-contracts-engineer` | 3 |
| 21 | `ingestion/src/ingestion/contract.py` | Create | Avaliador do contrato nos pontos Bronze→Silver e Gold (D4) | `data-quality-analyst` | 20 |
| 22 | `ingestion/sql/silver/debt_state.sql` | Create | Normalização (formato Dataform, D2); ente não mapeado ⇒ falha | `sql-optimizer` | 6,19 |
| 23 | `ingestion/sql/gold/gold_debt_state_current.sql` | Create | `MERGE` idempotente; `data_class='observed'` | `sql-optimizer` | 22 |
| 24 | `ingestion/src/ingestion/provenance.py` | Create | Escreve `metric_provenance` (`SPEC-007`, `confidence=1.0`) | `ai-data-engineer-gcp` | 23 |
| 25 | `ingestion/src/ingestion/pipeline.py` | Create | Orquestra C8→…→C4(gold); `run_id`, counts, errors (`SPEC-002`) | `ai-data-engineer-gcp` | 15,16,17,21,22,23,24 |
| 26 | `ingestion/tests/test_connector.py` | Create | discover/metadata/checkpoint; retry registrado (AT2 parcial) | `python-reviewer` | 15 |
| 27 | `ingestion/tests/test_raw_immutability.py` | Create | AT2 — não sobrescreve, hash no nome | `python-reviewer` | 16 |
| 28 | `ingestion/tests/test_silver_normalization.py` | Create | AT4 — de-para, DATE, NUMERIC, ente não mapeado falha | `data-quality-analyst` | 22 |
| 29 | `ingestion/tests/test_contract_gold.py` | Create | AT7/S2/S1 — schema, NOT NULL, `value>=0`, 28 linhas, cobertura provenance (R-006) | `data-quality-analyst` | 21,23,24 |
| 30 | `ingestion/tests/test_contract_bronze_drift.py` | Create | R-006 — drift de origem ⇒ quarentena antes da Silver (D4) | `data-quality-analyst` | 21 |
| 31 | `ingestion/tests/test_output_classification.py` | Create | R-003 — Gold e provenance carregam `observed` (AT6) | `data-quality-analyst` | 23,24 |
| 32 | `.github/workflows/data.yml` | Create | Gates PR1: ruff+black, mypy, pytest unit+integration, contract, `terraform validate/plan` via WIF, spec-verify | `ci-cd-specialist` | 9,10,21,25 |
| 33 | `.github/workflows/security.yml` | Create | Secret scan (gitleaks) em todo PR (R-011) | `security-reviewer` | — |
| 34 | `.github/CODEOWNERS` | Modify | `infra/**`→infra owners; `ingestion/contracts/**`, `docs/adrs/**`, `docs/specs/**`→owners (`SPEC-032`) | `(general)` | — |
| 35 | `ingestion/README.md` | Create | Como rodar o job local/dev; `gcloud run jobs execute` (OQ7) | `code-documenter` | 25 |

### PR2 — apresentação

| # | Arquivo | Ação | Propósito | Agente | Deps |
|---|---|---|---|---|---|
| 36 | `api/pyproject.toml` `Dockerfile` | Create | Pacote FastAPI + imagem | `python-developer` | — |
| 37 | `api/src/api/config.yaml` | Create | project, dataset Gold, `metric_id` default | `(general)` | — |
| 38 | `api/src/api/models.py` | Create | Pydantic v2: `MetricResponse` (com `data_class`), `ProvenanceResponse` (`SPEC-007`) | `python-developer` | — |
| 39 | `api/src/api/bigquery_repo.py` | Create | Query Gold (`MAX(reference_date)`) + `metric_provenance`; resolve cadeia SPEC-007 | `sql-optimizer` | 37 |
| 40 | `api/src/api/main.py` | Create | `GET /v1/metrics/{id}`, `GET /v1/provenance/{metric_id}`, `/openapi.json` (D3) | `python-developer` | 38,39 |
| 41 | `api/tests/test_metrics_endpoint.py` | Create | AT9 — value/unit/reference_date/`data_class` + provenance resumido | `python-reviewer` | 40 |
| 42 | `api/tests/test_provenance_endpoint.py` | Create | AT9/SPEC-007 — cadeia completa, trust status | `python-reviewer` | 40 |
| 43 | `api/scripts/export_openapi.py` | Create | Dump de `openapi.json` para o CI (ADR-024) | `python-developer` | 40 |
| 44 | `web/package.json` `tsconfig.json` `vite.config.ts` | Create | Projeto Vite + TS | `(general)` | — |
| 45 | `web/Dockerfile` | Create | Imagem estática (`nginx:alpine`) servindo `dist/` | `ci-cd-specialist` | 44 |
| 46 | `web/scripts/gen-client.sh` | Create | `openapi-typescript openapi.json → src/api-client/` (ADR-024) | `(general)` | 43 |
| 47 | `web/src/api-client/**` | Create (gerado) | DTOs + fetch tipado — não editar à mão | `(general)` | 46 |
| 48 | `web/index.html` `web/src/main.ts` | Create | 1 card: fetch via cliente, valor, `reference_date`, link "fonte", selo `data_class` | `(general)` | 47 |
| 49 | `web/src/styles.css` | Create | Tratamento visual `observed/estimated/simulated` (ADR-028); contraste/foco (a11y) | `a11y-architect` | 48 |
| 50 | `web/tests/e2e/card.spec.ts` | Create | AT10 — valor vem da API, link correto, selo `observed`, grep do bundle sem número | `e2e-runner` | 48 |
| 51 | `infra/terraform/cloud_run.tf` | Modify | + Cloud Run **Service** api e web; IAM invoker público na web (ADR-044) | `gcp-data-architect` | 8 |
| 52 | `infra/terraform/iam.tf` | Modify | SA da API: `bigquery.jobUser` + `dataViewer` só no dataset Gold | `ci-cd-specialist` | 9 |
| 53 | `.github/workflows/api-web.yml` | Create | Gates PR2: ruff/mypy, pytest api, `export_openapi` + diff check, `gen-client` + diff check, tsc, playwright e2e, terraform, spec-verify | `ci-cd-specialist` | 43,46,50 |
| 54 | `.github/CODEOWNERS` | Modify | `api/**`, `web/**` owners | `(general)` | — |
| 55 | `docs/specs/SPEC-033-...` | Modify | Marcar requisitos PR2 como atendidos; evidências | `architect` | 3 |
| 56 | `api/README.md` `web/README.md` | Create | Rodar local, gerar cliente, deploy | `code-documenter` | 40,48 |

### Racional de atribuição de agentes

- **`.tf` → `gcp-data-architect`** (recursos GCP) **e `ci-cd-specialist`** (WIF, IAM, budget, workflows) — arquivos divididos por sub-tópico.
- **Ingestão Python com BigQuery/GCS → `ai-data-engineer-gcp`** (palavras-chave: Cloud Run, BigQuery, pipeline); módulos utilitários sem GCP → `python-developer`.
- **SQL → `sql-optimizer`** (BigQuery SQL; não há agente Dataform/BQ dedicado).
- **Contrato → `data-contracts-engineer`**; **testes de qualidade/contrato → `data-quality-analyst`**.
- **API FastAPI/Pydantic → `python-developer`**, revisão `python-reviewer`; query → `sql-optimizer`.
- **Web TS:** sem agente autor de TS na lista — autoria `(general)`, **revisão `typescript-reviewer`**; acessibilidade e CSS do selo → `a11y-architect`; e2e → `e2e-runner`.
- **Docs ADR/SPEC → `architect`**; READMEs → `code-documenter`.
- **Revisão transversal:** `code-reviewer` + `security-reviewer` em ambos os PRs (não listados por arquivo).

### Independência das unidades implantáveis

- `ingestion/`, `api/`, `web/` são pacotes separados, sem import cruzado.
- Único acoplamento: `api` gera `openapi.json` → `web` gera `src/api-client/` a partir dele **no CI** (ADR-024). É dependência de artefato de build, não de código-fonte compartilhado.
- Sem ciclo: `pipeline` é linear; `api` só lê BigQuery; `web` só chama `api`.

---

## 5. Padrões de código

### 5.1 Interface de connector (SPEC-003)

```python
# ingestion/src/ingestion/connectors/base.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ResourceRef:
    dataset_id: str
    resource_url: str
    resource_format: str          # "csv" | "xlsx"
    resource_hash: str | None     # sha256 do último download conhecido (checkpoint)


class Connector(Protocol):
    def discover(self) -> ResourceRef: ...
    def metadata(self, ref: ResourceRef) -> dict: ...
    def download(self, ref: ResourceRef, dest: str) -> str:   # retorna path local
        ...
    def validate(self, local_path: str) -> None:              # levanta em formato inesperado
        ...
    def checkpoint(self, ref: ResourceRef, content_sha256: str) -> bool:
        """True se o hash mudou (deve ingerir); False se igual (no-op)."""
        ...
```

### 5.2 Escrita RAW imutável (ADR-005 / SPEC-004)

```python
# ingestion/src/ingestion/raw.py
import hashlib, json, datetime as dt
from google.cloud import storage


def write_raw(bucket: str, prefix: str, local_path: str, source_uri: str) -> str:
    data = open(local_path, "rb").read()
    sha = hashlib.sha256(data).hexdigest()
    ext = local_path.rsplit(".", 1)[-1].lower()
    blob_name = f"{prefix}/{sha}.{ext}"
    client = storage.Client()
    bkt = client.bucket(bucket)
    blob = bkt.blob(blob_name)
    if not blob.exists():                       # nunca sobrescreve
        blob.upload_from_string(data, if_generation_match=0)
    manifest = {
        "source_uri": source_uri,
        "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "bytes": len(data),
        "content_sha256": sha,
    }
    m = bkt.blob(f"{prefix}/{sha}.manifest.json")
    if not m.exists():
        m.upload_from_string(json.dumps(manifest, indent=2), if_generation_match=0)
    return f"gs://{bucket}/{blob_name}"
```

### 5.3 Contrato de dados (SPEC-005) — trecho

```yaml
# ingestion/contracts/divida_consolidada_estados.yaml
dataset: divida_consolidada_estados
version: 1                       # imutável após release
keys: [state_ibge_code, reference_date]
required_fields:
  state_ibge_code: {type: STRING, nullable: false}
  reference_date:  {type: DATE,   nullable: false}
  value:           {type: NUMERIC, nullable: false, min: 0}
  unit:            {type: STRING, nullable: false, allowed: [BRL]}
null_thresholds: {value: 0.0}
freshness: {max_age_days: 400}   # DCL é publicada com baixa frequência
quality_rules:
  - name: completeness_28_entes
    expr: "count(distinct state_ibge_code) = 28"
  - name: provenance_coverage
    expr: "every metric row has a metric_provenance row"
evolution_policy: additive_only  # mudança que quebra ⇒ nova versão
```

### 5.4 Modelo SQL no formato Dataform (D2)

```sql
-- ingestion/sql/gold/gold_debt_state_current.sql
-- (executado via cliente BigQuery na fatia #1; migra para Dataform sem reescrita)
MERGE `${project}.br2036_gold.gold_debt_state_current` T
USING (
  SELECT
    s.state_ibge_code,
    s.state_name,
    s.reference_date,
    'divida_consolidada_liquida' AS metric_id,
    s.value,
    'BRL'       AS unit,
    'observed'  AS data_class          -- ADR-028
  FROM `${project}.br2036_silver.debt_state` s
) SRC
ON  T.state_ibge_code = SRC.state_ibge_code
AND T.reference_date  = SRC.reference_date
AND T.metric_id       = SRC.metric_id
WHEN MATCHED THEN UPDATE SET value = SRC.value, unit = SRC.unit, data_class = SRC.data_class
WHEN NOT MATCHED THEN INSERT ROW;
```

### 5.5 API — modelos e endpoints (SPEC-007 / SPEC-026 / ADR-028)

```python
# api/src/api/models.py
from enum import Enum
from pydantic import BaseModel


class DataClass(str, Enum):
    observed = "observed"
    estimated = "estimated"
    simulated = "simulated"


class ProvenanceSummary(BaseModel):
    source: str
    reference_date: str
    trust_status: str


class MetricResponse(BaseModel):
    metric_id: str
    state_ibge_code: str
    value: float
    unit: str
    reference_date: str
    data_class: DataClass          # tipado em API (ADR-028)
    provenance: ProvenanceSummary


class ProvenanceResponse(BaseModel):   # GET /v1/provenance/{metric_id} — SPEC-007
    metric_id: str
    gold_object: str
    silver_transform: str
    silver_transform_version: str
    bronze_object: str
    source_resource_url: str
    catalog_dataset_id: str
    producing_organization: str
    reference_date: str
    trust_status: str
```

```python
# api/src/api/main.py
from fastapi import FastAPI, HTTPException
from .models import MetricResponse, ProvenanceResponse
from .bigquery_repo import get_latest_metric, resolve_provenance

app = FastAPI(title="BRASIL 2036 — Metrics API", version="1.0.0")


@app.get("/v1/metrics/{metric_id}", response_model=MetricResponse)
def metrics(metric_id: str, state_ibge_code: str = "35"):
    row = get_latest_metric(metric_id, state_ibge_code)
    if row is None:
        raise HTTPException(404, "metric not found")
    return row


@app.get("/v1/provenance/{metric_id}", response_model=ProvenanceResponse)
def provenance(metric_id: str, state_ibge_code: str = "35"):
    row = resolve_provenance(metric_id, state_ibge_code)
    if row is None:
        raise HTTPException(404, "provenance not found")
    return row
```

### 5.6 Card — consumo tipado, sem número no bundle (ADR-012 / ADR-024 / ADR-028)

```typescript
// web/src/main.ts
import createClient from "./api-client";           // gerado de openapi.json

const client = createClient({ baseUrl: import.meta.env.VITE_API_URL });

async function render() {
  const { data, error } = await client.GET("/v1/metrics/{metric_id}", {
    params: { path: { metric_id: "divida_consolidada_liquida" },
              query: { state_ibge_code: "35" } },
  });
  const el = document.querySelector("#card")!;
  if (error || !data) { el.textContent = "indisponível"; return; }
  el.innerHTML = `
    <span class="data-class data-class--${data.data_class}">${data.data_class}</span>
    <p class="value">${new Intl.NumberFormat("pt-BR",
      { style: "currency", currency: data.unit }).format(data.value)}</p>
    <p class="ref">referência: ${data.reference_date}</p>
    <a class="source" href="${data.provenance.source}" target="_blank" rel="noopener">fonte</a>`;
}
render();
```

---

## 6. Estratégia de testes

| Tipo | Escopo | Ferramentas | Cobre |
|---|---|---|---|
| Unit | `raw.write` (imutabilidade), `connector` (checkpoint/retry), parsing Silver isolado, avaliador de contrato | pytest | AT2, AT3(parcial), R-006 |
| Integration (dados) | pipeline contra BigQuery de dev (ou emulador): registry, Bronze load, Silver, Gold, provenance | pytest + BigQuery client | AT1, AT3, AT4, AT5, AT6, S1, S2, S7 |
| Contract | `contract.check` Bronze→Silver e Gold como **gate de CI** | pytest + YAML | AT7, R-006 (`contract_test_breaking_drift`) |
| Classification | Gold + provenance carregam `observed` | pytest | AT6, R-003 (`test_output_classification`) |
| Infra | `terraform validate`; `terraform plan` sem exposição não-ADR; `tfsec`/`checkov`; secret scan | Actions + WIF | AT8, S5, R-011 (`secret_scan`) |
| API | endpoints `/v1/metrics` e `/v1/provenance`; shape SPEC-007; `data_class` presente | pytest + httpx | AT9 |
| Contract (API) | `openapi.json` regenerado == commitado; cliente TS regenerado == commitado | Actions diff-check | ADR-024 / SPEC-026 |
| E2E | card renderiza valor da API, link "fonte" correto, selo `observed`; grep do bundle não acha o número | Playwright (`e2e-runner`) | AT10, S6 |
| Ritual | todos os gates verdes; `agent-eval` marcado N/A (sem agente — SPEC-031 "quando afetados"); `/verify-spec` PASS por requisito | Actions + sessão de review | AT11, S3, S4 |
| Cost guardrail | `terraform plan` inclui budget; teste afirma budget presente no projeto dev | Actions | R-012 (`cost_guardrail_test`) |
| Freshness (mínimo) | contrato tem `freshness`; manifest/registry gravam `last_resource_update`; teste afirma metadados de freshness preenchidos | pytest | R-008 (`test_stale_source_block`, versão mínima) |

**Rastreabilidade AT → teste:** AT1→integration(registry); AT2→unit(raw)+unit(connector); AT3→integration(bronze); AT4→unit+integration(silver, incl. ente não mapeado falha); AT5→integration(gold); AT6→integration(provenance)+classification; AT7→contract gate; AT8→infra; AT9→API(2 testes); AT10→E2E; AT11→ritual de CI + `/verify-spec`.

---

## 7. Pipeline Architecture (contexto de Data Engineering)

### 7.1 DAG (linear, orquestrado por `pipeline.py`)

```text
registry.upsert
  └─▶ connector.discover ─▶ connector.checkpoint ──(hash igual)──▶ [FIM: no-op]
        └─(hash novo)─▶ connector.download ─▶ raw.write ─▶ bronze.load
              └─▶ contract.check(bronze) ──(fail)──▶ [quarentena · exit≠0 · alerta]
                    └─(pass)─▶ silver.sql ─▶ gold.sql ─▶ provenance.write
                          └─▶ contract.check(gold) ──(fail)──▶ [exit≠0 · alerta]
                                └─(pass)─▶ [FIM: ok · run_id registrado]
```

### 7.2 Estratégia de partição

| Tabela | Partição | Cluster | Nota |
|---|---|---|---|
| `br2036_bronze.debt_state_raw` | `_ingested_at` (DATE) | — | histórico de cargas |
| `br2036_silver.debt_state` | `reference_date` (DATE) | `state_ibge_code` | convenção; volume trivial |
| `br2036_gold.gold_debt_state_current` | `reference_date` (DATE) | `state_ibge_code` | idem |
| `br2036_gold.metric_provenance` | `reference_date` (DATE) | `metric_id` | idem |

### 7.3 Estratégia incremental

- **Download:** checkpoint por `content_sha256` (SPEC-003) — pula recarga se inalterado.
- **Bronze:** append (cada carga é um snapshot rastreável por `_row_hash` / `_ingested_at`).
- **Silver/Gold:** `MERGE` por `(state_ibge_code, reference_date[, metric_id])` — re-execução é idempotente.
- **Provenance:** `MERGE` pela mesma chave + `metric_id`.
- Sem CDC, sem streaming (volume ~28 linhas/período).

### 7.4 Evolução de schema

- Contrato `version: 1` imutável (SPEC-005). Mudança pretendida ⇒ **nova versão** de contrato + PR.
- Drift **que quebra** na origem (coluna sumida, tipo incompatível) ⇒ `contract.check(bronze)` falha ⇒ **nada promovido para Silver** ⇒ estado `quarantined`, exit ≠ 0, log de alerta (SPEC-004, R-006).
- Drift **aditivo** (coluna nova irrelevante) ⇒ ignorado na Silver (seleção explícita de colunas).

### 7.5 Data quality gates

| Gate | Onde | Regra | Falha ⇒ |
|---|---|---|---|
| Schema origem | após Bronze | colunas/keys esperadas do contrato v1 | quarentena, sem Silver |
| Territorial | Silver | todo ente casa em `ref_estado_ibge` | erro, run falha |
| Completude | após Gold | 28 entes para a `reference_date` corrente | run falha |
| Integridade | após Gold | `NOT NULL` em PK, `value >= 0` | run falha |
| Provenance | após Gold | 100% das linhas de métrica com linha em `metric_provenance` | run falha |
| Classificação | após Gold | `data_class = 'observed'` e `scenario='observed'` | run falha (R-003) |
| Freshness (mín.) | contrato + registry | `last_resource_update` gravado; idade ≤ `max_age_days` | warning na fatia #1 (bloqueio pleno adiado) |

---

## 8. Quality gate (Fase 2)

- [x] Padrões carregados dos domínios do DEFINE — via SPEC-002/003/004/005/007/026/031 e ADRs (não há `kb/`); confiança 0.82 documentada.
- [x] Diagrama ASCII de arquitetura criado e legível (§2.1).
- [x] Ao menos uma decisão com racional completo — D1, D2, D3, D4, D5 (cinco ADRs inline completos).
- [x] Manifesto de arquivos completo — 56 itens (PR1: 1–35; PR2: 36–56).
- [x] Agente atribuído a cada arquivo (ou `(general)`), com racional (§4).
- [x] Padrões de código sintaticamente corretos e prontos para colar (§5).
- [x] Estratégia de testes cobre todos os ATs — matriz de rastreabilidade AT→teste (§6).
- [x] Sem dependência compartilhada entre unidades implantáveis — só artefato de build `openapi.json → cliente TS` (§4).
- [x] Sem dependência circular — pipeline linear; api só lê BQ; web só chama api.
- [x] Status do DEFINE atualizado para `✅ Complete (Designed)`.

**Contract gate (`spec-lint`):** não executável (plugin ausente) — validar manualmente quando disponível.

---

## 9. Handoff

Pronto para **`/build .claude/sdd/features/DESIGN_MVP_WALKING_SKELETON.md`**.

Ordem de build sugerida (respeitando dependências do manifesto):
1. **Docs primeiro:** ADR-051, amendment ADR-007, SPEC-033 (itens 1–3) — destravam D2/D5/D6.
2. **PR1:** Terraform (4–11) → contrato (19–20) → ingestão (12–18, 21–25) → testes (26–31) → CI de dados (32–35).
3. **PR2:** API (36–43) → web (44–50) → Terraform services (51–52) → CI api/web (53) → CODEOWNERS/SPEC/READMEs (54–56).

---

## 10. Revision history

| Data | Versão | Mudança | Autor |
|---|---|---|---|
| 2026-09-03 | 1.0 | Criação a partir de `DEFINE_MVP_WALKING_SKELETON.md`. 5 ADRs inline, 56 itens de manifesto, OQ1–OQ8 resolvidas. Status → Ready for Build. | /design (Claude Sonnet 5) |
