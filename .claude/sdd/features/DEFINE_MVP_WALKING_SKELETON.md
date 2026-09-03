# DEFINE — MVP_WALKING_SKELETON

## Metadados

- **Feature:** MVP_WALKING_SKELETON
- **Status:** ✅ Complete (Designed)
- **Fase:** 1 (Define)
- **Entrada:** `.claude/sdd/features/BRAINSTORM_MVP_WALKING_SKELETON.md` (tipo: `brainstorm_document`)
- **Criado:** 2026-09-03
- **Idioma:** PT-BR
- **Clarity score:** 14/15 (HIGH)
- **Design:** `.claude/sdd/features/DESIGN_MVP_WALKING_SKELETON.md` (2026-09-03)
- **Próximo passo:** `/build .claude/sdd/features/DESIGN_MVP_WALKING_SKELETON.md`

> Nota de ambiente: os assets do plugin SDD (`DEFINE_TEMPLATE.md`, `WORKFLOW_CONTRACTS.yaml`,
> `kb/_index.yaml`, `tools/spec-linter`) não estão instalados neste projeto. O documento segue
> a lista de seções obrigatórias descrita no skill `sdd-define`. O **contract gate (spec-lint)
> não pôde ser executado** — validar manualmente contra o contrato quando o plugin estiver disponível.

---

## 1. Problem statement

O repositório BRASIL 2036 tem 18 PRDs, 32 SPECs e 50 ADRs, mas **nenhuma cadeia de dados
provada ponta a ponta**: nenhum SPEC de módulo pode ser construído com confiança porque
todos pressupõem infraestrutura, camadas de dados e provenance que ainda não existem.
É preciso a fatia vertical mais fina possível que prove — com um dataset aberto real — o
caminho `dados.gov.br → RAW → Bronze → Silver → Gold → métrica canônica com provenance →
apresentação`, com o ritual de CI todo verde e nada burlado.

---

## 2. Target users

| Persona | Descrição | Pain point |
|---|---|---|
| **Time de implementação / agentes de código do BRASIL 2036** (primária) | Quem vai construir os módulos M01–M18 seguindo os SPECs | Não há padrão de pipeline provado para replicar; cada SPEC de módulo assume RAW/Bronze/Silver/Gold, provenance, Terraform e gates de CI que não existem. Risco alto de retrabalho no primeiro módulo. |
| **Avaliador do 2º Concurso de Reúso de Dados Abertos da CGU** (secundária) | Julga apresentação, transparência e uso de dados abertos | Precisa ver, em minutos, um indicador real derivado de dado aberto oficial **com fonte, data e metodologia rastreáveis** — não um mockup. |
| **Cidadão / jornalista / pesquisador** (secundária) | Visitante do portal público (PRD-001) | Quer entender um número sobre o Brasil e chegar à fonte oficial em poucos cliques, distinguindo observado de estimado/simulado. |

---

## 3. Goals (MoSCoW)

### MUST
- **G1.** Provar a cadeia completa com o dataset **"Dívida Consolidada dos Estados e do DF"**: recurso real do dados.gov.br até uma métrica canônica no BigQuery Gold.
- **G2.** Emitir **objeto de provenance completo** (`SPEC-007`) para cada linha de métrica: `value, unit, source, reference_date, model, model_version, scenario, confidence, assumptions[]`.
- **G3.** RAW **imutável** em GCS (hash de conteúdo no nome do objeto); camadas Bronze/Silver/Gold em BigQuery (ADR-003, ADR-005, ADR-006).
- **G4.** Infra criada **só por Terraform** num único projeto GCP dev; CI autentica por **Workload Identity Federation**, sem chave estática (ADR-039, ADR-040, `SPEC-001`).
- **G5.** **Um card** na Landing pública exibindo o valor + `reference_date` + link para a fonte real, marcado visualmente como `observed` (ADR-028), consumindo o dado por **API** — nenhum número hard-coded (ADR-012).
- **G6.** **Ritual de CI todo verde**: format → lint → typecheck → unit → integration → data-contract → security → `terraform validate/plan` → spec-verifier. `agent-eval` = N/A (sem agente). `/verify-spec` PASS por requisito.
- **G7.** Entrega em **duas PRs** (Abordagem B): PR1 espinha de dados; PR2 API + card + deploy.

### SHOULD
- **G8.** Arquivos SQL de transformação no **formato Dataform** (um `.sql` por modelo, nomes referenciáveis), mesmo executados como BigQuery SQL puro na fatia — para migração barata ao Dataform depois (ADR-007).
- **G9.** Um **teste de data-contract mínimo** sobre a Gold, ligado ao gate de CI (schema + NOT NULL em `state_ibge_code`, `reference_date`, `value`; `value >= 0`).
- **G10.** API gerando **OpenAPI** a partir de Pydantic (ADR-024/SPEC-026), mesmo com um único endpoint.

### COULD
- **G11.** Gatilho agendado (Cloud Scheduler) para o connector — caso contrário, execução manual do Cloud Run Job.
- **G12.** Mais de um estado no card / seletor de estado (o MVP exige só um valor exibível).

---

## 4. Success criteria (mensuráveis)

| # | Critério | Medição |
|---|---|---|
| S1 | Cobertura de provenance | **100%** das linhas de `gold_debt_state_current` têm linha correspondente em `metric_provenance` com todos os campos `SPEC-007` não-nulos. |
| S2 | Completude da carga | Para a `reference_date` escolhida, **27 estados + DF = 28** linhas na Gold; zero nulos em `state_ibge_code`/`reference_date`/`value`. |
| S3 | Verificação independente | `/verify-spec` retorna **PASS em 100%** dos requisitos, em sessão nova read-only. |
| S4 | Gates de CI | **Todos** os gates obrigatórios verdes num PR; nenhum marcado como skip exceto `agent-eval` (N/A documentado). |
| S5 | Sem segredo / sem exposição | `terraform plan` sem exposição pública não declarada em ADR; **zero** chave estática no repo (scan de `/security-check`). |
| S6 | Card fiel à fonte | O card renderiza valor obtido da API (não do bundle) e o link "fonte" abre o `source_url` real registrado em `dataset_registry`. |
| S7 | Rastreabilidade fim-a-fim | Uma query cruzando `dataset_registry → GCS RAW (uri) → Bronze (_row_hash) → Silver → Gold → metric_provenance` fecha para pelo menos um estado numa `reference_date`. |
| S8 | Tamanho de PR | Cada PR (PR1, PR2) revisável isoladamente; PR1 não contém código de frontend, PR2 não altera lógica de pipeline. |

---

## 5. Acceptance tests

- **AT1 — Discovery/registry.** *Given* o catálogo dados.gov.br, *When* o dataset "Dívida Consolidada dos Estados e do DF" é resolvido, *Then* `br2036_control.dataset_registry` tem exatamente **uma** linha `active=true` com `source_url`, `resource_url`, `resource_format`, `license`, `br2036_domain='fiscal'`, `br2036_module='M02'`.
- **AT2 — RAW imutável.** *Given* o mesmo recurso baixado duas vezes com conteúdo idêntico, *When* o connector grava em GCS RAW, *Then* o nome do objeto contém o SHA-256 do conteúdo e a segunda execução **não** sobrescreve nem duplica o objeto.
- **AT3 — Bronze.** *Given* um objeto RAW, *When* carregado em Bronze, *Then* `br2036_bronze.debt_state_raw` tem `_source_uri`, `_ingested_at`, `_row_hash` em toda linha e a contagem de colunas bate com a origem.
- **AT4 — Silver.** *Given* linhas Bronze, *When* o SQL Silver roda, *Then* toda linha tem `state_ibge_code` não-nulo resolvido pela tabela de-para, `reference_date` DATE válida e `value` NUMERIC em BRL; ente não reconhecido **falha a execução** (sem descarte silencioso).
- **AT5 — Gold.** *Given* Silver, *When* o SQL Gold roda, *Then* `gold_debt_state_current` tem uma linha por `(state_ibge_code, reference_date)` com `metric_id='divida_consolidada_liquida'` e `unit='BRL'`.
- **AT6 — Provenance.** *Given* linhas Gold, *Then* `metric_provenance` tem uma linha por linha de métrica, com `scenario='observed'`, `model='none'`, `confidence` preenchido e `assumptions[]` presente.
- **AT7 — Data-contract.** *Given* a tabela Gold, *When* o teste de contrato roda no CI, *Then* schema confere, `NOT NULL` vale em `state_ibge_code`/`reference_date`/`value`, `value >= 0`; qualquer violação **quebra o CI**.
- **AT8 — Terraform/WIF.** *Given* a config de infra, *When* `terraform validate` e `plan` rodam no CI via WIF, *Then* não há chave estática no repo e o plan não declara exposição pública fora de ADR.
- **AT9 — API.** *Given* Gold + provenance, *When* `GET /v1/metrics/divida_consolidada_liquida?state_ibge_code=35`, *Then* a resposta tem `value`, `unit`, `reference_date` e um objeto `provenance` não-nulo com todos os campos `SPEC-007`.
- **AT10 — Card.** *Given* a página publicada, *When* renderiza, *Then* o card mostra valor, `reference_date` e link "fonte" para o `source_url` real, marcado como `observed`, com o valor vindo da API (sem número hard-coded no bundle).
- **AT11 — Ritual.** *Given* um PR, *When* o CI roda, *Then* format, lint, typecheck, unit, integration, data-contract, security, `terraform validate/plan`, spec-verifier passam; `agent-eval` marcado N/A; `/verify-spec` PASS por requisito.

---

## 6. Out of scope

| Item | Motivo | Destino |
|---|---|---|
| Dataset **INSS** (Benefícios Emitidos) | Dois datasets na 1ª fatia anulam o de-risking | Fatia #2 (mesmo padrão de pipeline) |
| GCP Foundation completa (org/folders, stg/prod, budgets, log sinks) | A fatia usa 1 projeto dev e ~5 recursos | `SPEC-001` próprio |
| Adoção de **Dataform** (workspace, release config, CI) | Sem retorno com 2 modelos; amplia superfície da fatia | Incremento que levanta os `.sql` para o Dataform (ADR-007) |
| **Data Trust Score** (`SPEC-006`) | Score composto não é necessário para provar provenance | Incremento pós-fatia |
| **Semantic Layer** completo (`SPEC-008`) | A fatia define **uma** métrica, não a camada | `SPEC-008` próprio |
| **Séries históricas** no card | Walking skeleton = um valor atual | PRD-001 V1 |
| **Schema Drift Quarantine** completo (`SPEC-005` inteiro) | A fatia leva só um teste de contrato mínimo | `SPEC-005` próprio |
| **Observabilidade/tracing** full (`SPEC-025`) | Específico de agente; Cloud Run já dá logging básico | Quando entrar agente |
| **RAG / Copilot / agentes / auth / RBAC** | Fora do escopo da fatia; Landing é pública (ADR-044) | Fases posteriores |
| Gate **`agent-eval`** ativo | N/A — não há agente nesta fatia (documentado, não burlado) | Ativa quando houver agente |
| stg/prod, multi-região, HA, SLOs | Fatia roda só em dev | Fases de escala |
| Edição administrativa de métricas | Fora do PRD-001 V1 | Admin Center (M17) |

---

## 7. Constraints

- **C1.** Terraform é a única fonte de mudança de infra (ADR-039).
- **C2.** CI autentica por Workload Identity Federation; **nenhuma** chave JSON de longa duração (ADR-040, `SPEC-001`).
- **C3.** Segredos apenas em Secret Manager.
- **C4.** LLM nunca computa a métrica oficial (ADR-012); nenhum indicador hard-coded para produção (`CONTEXTO §16`).
- **C5.** Valores `observed` / `estimated` / `simulated` distintos visual e estruturalmente (ADR-028).
- **C6.** Landing pública, sem auth/RBAC (ADR-044).
- **C7.** `main` protegida, PR-only, Conventional Commits; sessões de review read-only.
- **C8.** Transformação SQL = BigQuery SQL na fatia (ADR-003); Dataform (ADR-007) adiado com nota de amendment — **questão aberta OQ2**.
- **C9.** Chave territorial = código IBGE de estado (ADR-011).
- **C10.** Um único projeto GCP dev; sem org/folders, sem stg/prod.
- **C11.** RAW nunca reescrito (ADR-005).
- **C12.** Toda resposta quantitativa carrega os 9 campos de provenance (`CONTEXTO §8`, `SPEC-007`).

---

## 8. Assumptions / risk register

| ID | Afirmação | Impacto se falsa | Validada |
|---|---|---|---|
| A1 | O recurso "Dívida Consolidada dos Estados e do DF" está hoje baixável no dados.gov.br em formato legível por máquina (CSV/XLSX) | Trocar de dataset P0 ou usar workaround de resource-resolver; fatia atrasa | ☐ |
| A2 | A DCL é publicada por estado por período com valor diretamente utilizável (sem derivação pesada para a métrica canônica) | Modelagem Silver/Gold cresce; pode exigir RCL para calcular razão | ☐ |
| A3 | Há um projeto GCP com billing disponível (ou criável) para o ambiente dev | Fallback para spike local mais curto, enfraquecendo o "ponta a ponta" | ☐ |
| A4 | Existe lookup estável nome-do-ente → código IBGE, versionável a partir do IBGE | Manter tabela de-para de 28 linhas no repo (impacto baixo) | ☐ |
| A5 | Os rituais `.claude/commands/*` (`/verify-spec`, `/security-check`, `/agent-eval`) rodam como estão contra esta fatia | Definir os equivalentes do repo antes (impacto baixo) | ☐ |
| A6 | Adiar Dataform (ADR-007) na fatia #1 é aceitável para os donos do ADR, com amendment registrado | Levantar Dataform já na fatia #1, aumentando o PR1 (impacto médio) | ☐ |
| A7 | Marcar `agent-eval` como N/A numa fatia sem agente não fere "nunca burlar gate obrigatório" | Precisar de mecanismo formal de waiver em `SPEC-031` | ☐ |
| A8 | Cloud Run + BigQuery + GCS + Artifact Registry + WIF cobrem a fatia sem outros serviços GCP | Ajuste de escopo de Terraform (impacto baixo) | ☐ |

---

## 9. Technical context

| Aspecto | Definição |
|---|---|
| **Onde vive** | Novos diretórios de implementação; layout exato decidido no `/design`. Candidatos: `connectors/` (Python, Cloud Run Job), `transform/` ou `sql/` (modelos BigQuery no formato Dataform), `infra/` (Terraform), `api/` (FastAPI), `web/` (Landing). |
| **Impacto IaC** | **SIM.** Terraform novo, 1 projeto dev: bucket GCS RAW, datasets BQ `control`/`bronze`/`silver`/`gold`, Artifact Registry, Cloud Run Job (connector), Cloud Run Service (API/página no PR2), service accounts com least privilege, WIF pool para o CI. Sem stg/prod, sem org/folders. |
| **Domínios de KB para o Design** | **PRDs:** PRD-001, PRD-002. **SPECs:** SPEC-001, SPEC-002, SPEC-003, SPEC-004, SPEC-005, SPEC-007, SPEC-008, SPEC-026, SPEC-031. **ADRs:** ADR-001/002, ADR-003, ADR-005/006, ADR-007, ADR-011, ADR-012, ADR-024, ADR-028, ADR-039/040, ADR-041, ADR-044. **Riscos:** `RISK-CONTROL-TEST-MATRIX.md`, `RISK-REGISTER.md`. **Discovery:** `07-MVP-BOUNDARIES.md`, `05-ASSURANCE-MATRIX.md`, `01-USER-JOURNEYS.md`. **Backlog:** EPIC-004/005/006/007/009/033. |

---

## 10. Data contract (aplicável)

### Source inventory
- **1 fonte:** recurso de arquivo do dados.gov.br — "Dívida Consolidada dos Estados e do DF" (origem: Tesouro Nacional / SICONFI). `source_url` e `resource_url` exatos = tarefa 1 (não há amostra).
- Formato esperado: CSV ou XLSX. Encoding e delimitador a confirmar na inspeção.

### Volumes
- ~**28 linhas por período de referência** (27 estados + DF). Histórico completo na ordem de centenas de linhas. **< 1 MB** total. Sem streaming.

### Freshness SLA
- Fatia #1: **batch, execução manual** do Cloud Run Job (ou Cloud Scheduler como COULD). Sem SLA rígido. Alvo: refletir o último extrato publicado.

### Schema contract (destino)
| Camada | Tabela | Colunas-chave |
|---|---|---|
| Bronze | `br2036_bronze.debt_state_raw` | todas as colunas de origem como `STRING` + `_source_uri STRING`, `_ingested_at TIMESTAMP`, `_row_hash STRING` |
| Silver | `br2036_silver.debt_state` | `state_ibge_code STRING`, `state_name STRING`, `reference_date DATE`, `value NUMERIC`, `unit STRING` (`'BRL'`), `_row_hash STRING` |
| Gold | `br2036_gold.gold_debt_state_current` | `state_ibge_code STRING`, `state_name STRING`, `reference_date DATE`, `metric_id STRING` (`'divida_consolidada_liquida'`), `value NUMERIC`, `unit STRING` (`'BRL'`) |
| Provenance | `br2036_gold.metric_provenance` | `metric_id`, `state_ibge_code`, `reference_date`, `value`, `unit`, `source`, `model`, `model_version`, `scenario` (`'observed'`), `confidence`, `assumptions ARRAY<STRING>` |

> Nomenclatura de datasets/tabelas a confirmar contra `CONTEXTO §10` no `/design` — **OQ6**.

### Completeness metrics
- 28/28 entes presentes para a `reference_date` publicada mais recente.
- Zero nulos em `state_ibge_code`, `reference_date`, `value`. `value >= 0`.
- Nenhum ente da origem descartado silenciosamente na Silver (ente não mapeado ⇒ falha).

### Lineage requirements
- `dataset_registry.dataset_id` → `resource_url` → objeto GCS RAW (nome com SHA-256) → `debt_state_raw._row_hash` → `debt_state` → `gold_debt_state_current` → `metric_provenance`.
- Cada camada mantém `_source_uri` / `_row_hash` suficientes para reconstruir o caminho (S7).

---

## 11. Clarity score breakdown

| Elemento | Nota | Nota máx | Observação |
|---|---|---|---|
| Problem | 3 | 3 | Uma frase, específica e acionável: falta cadeia provada ponta a ponta; construir a fatia vertical mínima. |
| Users | 2 | 3 | Persona primária (time/agentes de implementação) clara com pain point; personas secundárias (CGU, cidadão) herdadas de PRD-001. "Usuário" de um walking skeleton é parcialmente abstrato — daí 2. |
| Goals | 3 | 3 | 12 goals com MoSCoW; mensuráveis; ligados a ADRs/SPECs. |
| Success | 3 | 3 | 8 critérios testáveis com números (28 linhas, 100% provenance, 0 chaves, PASS 100%). |
| Scope | 3 | 3 | Fronteiras explícitas: tabela YAGNI de 12 itens com destino, split PR1/PR2, out-of-scope não vazio. |
| **Total** | **14** | **15** | **HIGH — prosseguir para `/design`.** |

---

## 12. Open questions

| ID | Questão | Resolver em | Notas |
|---|---|---|---|
| OQ1 | Stack de frontend da Landing | `/design` (ADR) | Critérios: build estático, LCP/acessibilidade dos SLOs de PRD-001, servível por Cloud Run. |
| OQ2 | Amendment do ADR-007 registrando "SQL BigQuery puro na fatia #1; Dataform a partir do incremento N+1" | `/design` ou ADR sucessor curto | Bloqueia A6. |
| OQ3 | Tabela de-para estado → `state_ibge_code`: fonte (IBGE), versionamento, dataset onde mora (`control`?) | `/design` | |
| OQ4 | Um SPEC cobrindo PR1+PR2 (dois ciclos de build) ou dois SPECs | `/design` | |
| OQ5 | Convenção de `confidence` quando `scenario='observed'` (ex.: `1.0`) | `/design`, alinhar `SPEC-007` | |
| OQ6 | Nomenclatura de datasets/tabelas vs `CONTEXTO §10` (`gold_debt_trajectory`, `gold_state_profile`) | `/design`, confirmar antes de criar | |
| OQ7 | Gatilho do connector: manual apenas (fatia #1) ou Cloud Scheduler | `/design` | Tende a manual. |
| OQ8 | Qual `reference_date` exibir no card quando há várias | `/design` | Tende a "última publicada". |

---

## 13. Revision history

| Data | Versão | Mudança | Autor |
|---|---|---|---|
| 2026-09-03 | 1.0 | Criação a partir de `BRAINSTORM_MVP_WALKING_SKELETON.md`. Clarity 14/15. Status → Ready for Design. | /define (Claude Sonnet 5) |
| 2026-09-03 | 1.1 | Fase 2 concluída. Status → ✅ Complete (Designed). OQ1–OQ8 resolvidas no DESIGN. Próximo passo → /build. | /design (Claude Sonnet 5) |
