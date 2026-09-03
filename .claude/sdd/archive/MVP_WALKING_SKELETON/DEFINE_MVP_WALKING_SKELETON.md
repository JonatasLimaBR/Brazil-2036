# DEFINE — MVP_WALKING_SKELETON

## Metadados

- **Feature:** MVP_WALKING_SKELETON
- **Status:** ✅ Shipped
- **Fase:** 1 (Define)
- **Entrada:** `.claude/sdd/features/BRAINSTORM_MVP_WALKING_SKELETON.md` (tipo: `brainstorm_document`)
- **Criado:** 2026-09-03
- **Idioma:** PT-BR
- **Clarity score:** 14/15 (HIGH)
- **Versão:** 1.3 (2026-09-03 — cascata DV1–DV3 + correção 26 estados + DF = 27)
- **Design:** `.claude/sdd/features/DESIGN_MVP_WALKING_SKELETON.md` v1.1 (2026-09-03)
- **Descoberta:** `.claude/sdd/features/DISCOVERY_MVP_WALKING_SKELETON.md` (2026-09-03)
- **Próximo passo:** `/verify-spec` (SPEC-033) em sessão nova → `/ship`

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
- **G1.** Provar a cadeia completa com o dataset **"Dívida Consolidada dos Estados e do DF"** (recurso CSV do Tesouro Transparente / CKAN, catalogado no dados.gov.br): do recurso real até a métrica canônica **`divida_consolidada`** (Dívida Consolidada bruta do PAF, anual por UF) no BigQuery Gold. Ver `.claude/sdd/features/DISCOVERY_MVP_WALKING_SKELETON.md`.
- **G2.** Emitir **objeto de provenance completo** (`SPEC-007`) para cada linha de métrica: `value, unit, source, reference_date, model, model_version, scenario, confidence, assumptions[]`.
- **G3.** RAW **imutável** em GCS (hash de conteúdo no nome do objeto); camadas Bronze/Silver/Gold em BigQuery (ADR-003, ADR-005, ADR-006).
- **G4.** Infra criada **só por Terraform** num único projeto GCP dev; CI autentica por **Workload Identity Federation**, sem chave estática (ADR-039, ADR-040, `SPEC-001`).
- **G5.** **Um card** na Landing pública exibindo o valor + `reference_year` + link para a fonte real, marcado visualmente como `observed` (ADR-028), consumindo o dado por **API** — nenhum número hard-coded (ADR-012).
- **G6.** **Ritual de CI todo verde**: format → lint → typecheck → unit → integration → data-contract → security → `terraform validate/plan` → spec-verifier. `agent-eval` = N/A (sem agente). `/verify-spec` PASS por requisito.
- **G7.** Entrega em **duas PRs** (Abordagem B): PR1 espinha de dados; PR2 API + card + deploy.

### SHOULD
- **G8.** Arquivos SQL de transformação no **formato Dataform** (um `.sql` por modelo, nomes referenciáveis), mesmo executados como BigQuery SQL puro na fatia — para migração barata ao Dataform depois (ADR-007).
- **G9.** Um **teste de data-contract mínimo** sobre a Gold, ligado ao gate de CI (schema + NOT NULL em `state_ibge_code`, `reference_year`, `reference_date`, `value`; `value >= 0`).
- **G10.** API gerando **OpenAPI** a partir de Pydantic (ADR-024/SPEC-026), mesmo com um único endpoint.

### COULD
- **G11.** Gatilho agendado (Cloud Scheduler) para o connector — caso contrário, execução manual do Cloud Run Job.
- **G12.** Mais de um estado no card / seletor de estado (o MVP exige só um valor exibível).

---

## 4. Success criteria (mensuráveis)

| # | Critério | Medição |
|---|---|---|
| S1 | Cobertura de provenance | **100%** das linhas de `gold_debt_state_current` têm linha correspondente em `metric_provenance` com todos os campos `SPEC-007` não-nulos. |
| S2 | Completude da carga | Para o `reference_year` escolhido (`MAX(reference_year)`), **26 estados + DF = 27** linhas na Gold; zero nulos em `state_ibge_code`/`reference_year`/`reference_date`/`value`. |
| S3 | Verificação independente | `/verify-spec` retorna **PASS em 100%** dos requisitos, em sessão nova read-only. |
| S4 | Gates de CI | **Todos** os gates obrigatórios verdes num PR; nenhum marcado como skip exceto `agent-eval` (N/A documentado). |
| S5 | Sem segredo / sem exposição | `terraform plan` sem exposição pública não declarada em ADR; **zero** chave estática no repo (scan de `/security-check`). |
| S6 | Card fiel à fonte | O card renderiza valor obtido da API (não do bundle) e o link "fonte" abre o `source_url` real registrado em `dataset_registry`. |
| S7 | Rastreabilidade fim-a-fim | Uma query cruzando `dataset_registry → GCS RAW (uri) → Bronze (_row_hash) → Silver → Gold → metric_provenance` fecha para pelo menos um estado num `reference_year`. |
| S8 | Tamanho de PR | Cada PR (PR1, PR2) revisável isoladamente; PR1 não contém código de frontend, PR2 não altera lógica de pipeline. |

---

## 5. Acceptance tests

- **AT1 — Discovery/registry.** *Given* o dataset "Dívida Consolidada dos Estados e do DF" (host: Tesouro Transparente / CKAN), *When* o recurso é resolvido, *Then* `br2036_control.dataset_registry` tem exatamente **uma** linha `active=true` com `source_url` (catálogo dados.gov.br — a confirmar), `resource_url` (URL do CSV no CKAN), `resource_format='csv'`, `license='ODbL'`, `organization='COREM/STN'`, `update_frequency='annual'`, `br2036_domain='fiscal'`, `br2036_module='M02'`.
- **AT2 — RAW imutável.** *Given* o mesmo recurso baixado duas vezes com conteúdo idêntico, *When* o connector grava em GCS RAW, *Then* o nome do objeto contém o SHA-256 do conteúdo e a segunda execução **não** sobrescreve nem duplica o objeto.
- **AT3 — Bronze.** *Given* um objeto RAW (CSV `UF;ANO;VALOR`, `;`), *When* carregado em Bronze, *Then* `br2036_bronze.debt_state_raw` tem `_source_uri`, `_ingested_at`, `_row_hash` em toda linha e as 3 colunas de origem como STRING.
- **AT4 — Silver.** *Given* linhas Bronze, *When* o SQL Silver roda, *Then* toda linha tem `state_ibge_code` não-nulo resolvido de `UF` (2 letras) pela tabela de-para, `reference_year INT` (de `ANO`), `reference_date = DATE(ANO,12,31)` e `value` NUMERIC em BRL (parsing `pt-BR`: milhar `.`, decimal `,`); `UF` não reconhecida **falha a execução** (sem descarte silencioso).
- **AT5 — Gold.** *Given* Silver, *When* o SQL Gold roda, *Then* `gold_debt_state_current` tem uma linha por `(state_ibge_code, reference_year)` com `metric_id='divida_consolidada'`, `unit='BRL'` e `reference_date` preenchida.
- **AT6 — Provenance.** *Given* linhas Gold, *Then* `metric_provenance` tem uma linha por linha de métrica, com `scenario='observed'`, `model='none'`, `confidence` preenchido e `assumptions[]` presente.
- **AT7 — Data-contract.** *Given* a tabela Gold, *When* o teste de contrato roda no CI, *Then* schema confere, `NOT NULL` vale em `state_ibge_code`/`reference_year`/`reference_date`/`value`, `value >= 0`; qualquer violação **quebra o CI**.
- **AT8 — Terraform/WIF.** *Given* a config de infra, *When* `terraform validate` e `plan` rodam no CI via WIF, *Then* não há chave estática no repo e o plan não declara exposição pública fora de ADR.
- **AT9 — API.** *Given* Gold + provenance, *When* `GET /v1/metrics/divida_consolidada?state_ibge_code=35`, *Then* a resposta tem `value`, `unit`, `reference_year`, `reference_date` e um objeto `provenance` não-nulo com todos os campos `SPEC-007`.
- **AT10 — Card.** *Given* a página publicada, *When* renderiza, *Then* o card mostra valor, `reference_year` e link "fonte" para o `source_url` real, marcado como `observed`, com o valor vindo da API (sem número hard-coded no bundle).
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
- **C8.** Transformação SQL = BigQuery SQL na fatia (ADR-003); Dataform (ADR-007) adiado — **resolvido por ADR-052** (refina ADR-007).
- **C9.** Chave territorial = código IBGE de estado (ADR-011); origem traz `UF` de 2 letras → de-para `uf_ibge`.
- **C10.** Um único projeto GCP dev; sem org/folders, sem stg/prod.
- **C11.** RAW nunca reescrito (ADR-005).
- **C12.** Toda resposta quantitativa carrega os 9 campos de provenance (`CONTEXTO §8`, `SPEC-007`).

---

## 8. Assumptions / risk register

| ID | Afirmação | Impacto se falsa | Validada |
|---|---|---|---|
| A1 | O recurso está baixável em formato legível por máquina | — | ☑ **2026-09-03** — CSV `;`, UTF-8, 5,6 KiB, no CKAN do Tesouro Transparente (DISCOVERY §1). |
| A2 | Valor publicado por ente por período, diretamente utilizável, sem derivação pesada | — | ☑ **2026-09-03 (com correção)** — valor direto **e anual** (`UF;ANO;VALOR`); porém é **Dívida Consolidada bruta (PAF)**, não DCL. Métrica da fatia = `divida_consolidada` (ver DESIGN D12). DCL/RCL fica fora de escopo. |
| A3 | Há um projeto GCP com billing disponível (ou criável) para o ambiente dev | Fallback para spike local mais curto, enfraquecendo o "ponta a ponta" | ☐ **pendente (P2)** |
| A4 | Existe lookup estável ente → código IBGE, versionável | — | ☑ **2026-09-03 (com correção)** — a chave da origem é `UF` de 2 letras; de-para `UF (2 letras) → código IBGE (2 dígitos)`, 27 linhas (26 estados + DF), em `ingestion/reference/uf_ibge.csv`. |
| A5 | Os rituais `.claude/commands/*` rodam como estão contra esta fatia | Definir os equivalentes do repo antes (impacto baixo) | ☐ |
| A6 | Adiar Dataform (ADR-007) na fatia #1 é aceitável para os donos do ADR | Levantar Dataform já na fatia #1, aumentando o PR1 (impacto médio) | ☑ **2026-09-03** — resolvido por **ADR-052** (refina, não substitui ADR-007). |
| A7 | Marcar `agent-eval` como N/A numa fatia sem agente não fere "nunca burlar gate obrigatório" | Precisar de mecanismo formal de waiver em `SPEC-031` | ☑ **2026-09-03** — `SPEC-031` diz "agent evals **quando afetados**"; sem agente ⇒ N/A legítimo. |
| A8 | Cloud Run + BigQuery + GCS + Artifact Registry + WIF cobrem a fatia sem outros serviços GCP | Ajuste de escopo de Terraform (impacto baixo) | ☐ |
| A9 | A URL do catálogo no dados.gov.br pode ser confirmada para `dataset_registry.source_url` | Registrar só `resource_url` (CKAN) e completar depois; risco de atribuição no concurso CGU | ☐ **pendente** — API do Portal exigiu chave (DISCOVERY §4) |

---

## 9. Technical context

| Aspecto | Definição |
|---|---|
| **Onde vive** | Novos diretórios de implementação; layout exato decidido no `/design`. Candidatos: `connectors/` (Python, Cloud Run Job), `transform/` ou `sql/` (modelos BigQuery no formato Dataform), `infra/` (Terraform), `api/` (FastAPI), `web/` (Landing). |
| **Impacto IaC** | **SIM.** Terraform novo, 1 projeto dev: bucket GCS RAW, datasets BQ `control`/`bronze`/`silver`/`gold`, Artifact Registry, Cloud Run Job (connector), Cloud Run Service (API/página no PR2), service accounts com least privilege, WIF pool para o CI. Sem stg/prod, sem org/folders. |
| **Domínios de KB para o Design** | **PRDs:** PRD-001, PRD-002. **SPECs:** SPEC-001, SPEC-002, SPEC-003, SPEC-004, SPEC-005, SPEC-007, SPEC-008, SPEC-026, SPEC-031. **ADRs:** ADR-001/002, ADR-003, ADR-005/006, ADR-007, ADR-011, ADR-012, ADR-024, ADR-028, ADR-039/040, ADR-041, ADR-044. **Riscos:** `RISK-CONTROL-TEST-MATRIX.md`, `RISK-REGISTER.md`. **Discovery:** `07-MVP-BOUNDARIES.md`, `05-ASSURANCE-MATRIX.md`, `01-USER-JOURNEYS.md`. **Backlog:** EPIC-004/005/006/007/009/033. |

---

## 10. Data contract (aplicável)

### Source inventory (validado 2026-09-03 — DISCOVERY §1/§2)
- **1 fonte:** recurso CSV "Dívida Consolidada" do dataset `divida-consolidada-estados` no CKAN do Tesouro Transparente (org **COREM/STN**; contexto PAF). Catalogado no dados.gov.br (URL a confirmar — A9).
- `resource_url`: `https://www.tesourotransparente.gov.br/ckan/dataset/01aa8c02-4f77-4fcf-a850-ff8f13decb00/resource/de4a234e-1712-4a50-8d31-ae4748a5f715/download/divida-consolidada-dos-estados---paf.csv`
- Recurso companheiro: `metadados.pdf` (dicionário de dados) — fora de escopo da fatia.
- **Formato:** CSV, delimitador `;`, decimal `,`, milhar `.`, UTF-8. Colunas: `UF` (2 letras), `ANO` (YYYY), `VALOR` (BRL, Dívida Consolidada **bruta**).
- **Licença:** ODbL. **Atualização:** anual.

### Volumes
- **Grão anual:** ~**27 linhas por `ANO`** (26 estados + DF). Cobertura 2015–2022 ⇒ **~216 linhas** totais. **< 10 KiB**. Sem streaming.

### Freshness SLA
- Fatia #1: **batch, execução manual** do Cloud Run Job (Cloud Scheduler é COULD). `freshness.max_age_days = 500` (atualização anual). Alvo: refletir o último `ANO` publicado.

### Schema contract (destino) — atualizado DV1/DV2/DV3
| Camada | Tabela | Colunas-chave |
|---|---|---|
| Bronze | `br2036_bronze.debt_state_raw` | `UF STRING`, `ANO STRING`, `VALOR STRING` + `_source_uri STRING`, `_ingested_at TIMESTAMP`, `_row_hash STRING` |
| Silver | `br2036_silver.debt_state` | `state_ibge_code STRING`, `state_name STRING`, `reference_year INT64`, `reference_date DATE` (`DATE(ANO,12,31)`), `value NUMERIC`, `unit STRING` (`'BRL'`), `_row_hash STRING` |
| Gold | `br2036_gold.gold_debt_state_current` | `state_ibge_code STRING`, `state_name STRING`, `reference_year INT64`, `reference_date DATE`, `metric_id STRING` (`'divida_consolidada'`), `value NUMERIC`, `unit STRING` (`'BRL'`), `data_class STRING` (`'observed'`) |
| Provenance | `br2036_gold.metric_provenance` | `metric_id`, `state_ibge_code`, `reference_year`, `reference_date`, `value`, `unit`, `source`, `model`, `model_version`, `scenario` (`'observed'`), `confidence`, `assumptions ARRAY<STRING>` |
| Ref | `br2036_control.uf_ibge` | `uf STRING` (2 letras), `state_ibge_code STRING` (2 dígitos), `state_name STRING` |

> Nomenclatura de datasets/tabelas a confirmar contra `CONTEXTO §10` no `/design` — **OQ6**.

### Completeness metrics
- 27/27 entes presentes para `MAX(reference_year)`.
- Zero nulos em `state_ibge_code`, `reference_year`, `reference_date`, `value`. `value >= 0`.
- Nenhuma `UF` da origem descartada silenciosamente na Silver (`UF` não mapeada ⇒ falha).

### Lineage requirements
- `dataset_registry.dataset_id` → `resource_url` (CKAN) → objeto GCS RAW (nome com SHA-256) → `debt_state_raw._row_hash` → `debt_state` → `gold_debt_state_current` → `metric_provenance`.
- Cada camada mantém `_source_uri` / `_row_hash` suficientes para reconstruir o caminho (S7).

---

## 11. Clarity score breakdown

| Elemento | Nota | Nota máx | Observação |
|---|---|---|---|
| Problem | 3 | 3 | Uma frase, específica e acionável: falta cadeia provada ponta a ponta; construir a fatia vertical mínima. |
| Users | 2 | 3 | Persona primária (time/agentes de implementação) clara com pain point; personas secundárias (CGU, cidadão) herdadas de PRD-001. "Usuário" de um walking skeleton é parcialmente abstrato — daí 2. |
| Goals | 3 | 3 | 12 goals com MoSCoW; mensuráveis; ligados a ADRs/SPECs. |
| Success | 3 | 3 | 8 critérios testáveis com números (27 linhas, 100% provenance, 0 chaves, PASS 100%). |
| Scope | 3 | 3 | Fronteiras explícitas: tabela YAGNI de 12 itens com destino, split PR1/PR2, out-of-scope não vazio. |
| **Total** | **14** | **15** | **HIGH — prosseguir para `/design`.** |

---

## 12. Open questions

| ID | Questão | Status | Resolução |
|---|---|---|---|
| OQ1 | Stack de frontend da Landing | ✅ resolvido | **ADR-051** — Vite + TypeScript vanilla, build estático em Cloud Run. |
| OQ2 | Ferramenta de execução SQL da fatia vs ADR-007 | ✅ resolvido | **ADR-052** — BigQuery SQL na fatia, arquivos no formato Dataform; refina ADR-007. |
| OQ3 | Tabela de-para → `state_ibge_code` | ✅ resolvido | `ingestion/reference/uf_ibge.csv` (`UF` 2 letras → IBGE 2 dígitos) → `br2036_control.uf_ibge` (DV3). |
| OQ4 | Um SPEC ou dois | ✅ resolvido | Um — **SPEC-033**, dois ciclos de build (DESIGN D6). |
| OQ5 | Convenção de `confidence` para `observed` | ✅ resolvido | `confidence = 1.0`; proposta como nota em `SPEC-007` (DESIGN OQ5). |
| OQ6 | Nomenclatura de datasets/tabelas vs `CONTEXTO §10` | ✅ resolvido | `gold_debt_state_current` (novo, específico); relação com `gold_debt_trajectory`/`gold_state_profile` = trabalho futuro (SPEC-033). |
| OQ7 | Gatilho do connector | ✅ resolvido | Manual (`gcloud run jobs execute`) na fatia #1; Scheduler é COULD (G11). |
| OQ8 | Qual período exibir no card | ✅ resolvido | `MAX(reference_year)` da Gold (grão anual, DV1). |
| OQ9 | URL do catálogo no dados.gov.br (`dataset_registry.source_url`) | ⏳ pendente | API do Portal exigiu chave (A9). Confirmar no Portal ou com chave; não bloqueia PR1. |

---

## 13. Revision history

| Data | Versão | Mudança | Autor |
|---|---|---|---|
| 2026-09-03 | 1.0 | Criação a partir de `BRAINSTORM_MVP_WALKING_SKELETON.md`. Clarity 14/15. Status → Ready for Design. | /define (Claude Sonnet 5) |
| 2026-09-03 | 1.1 | Fase 2 concluída. Status → ✅ Complete (Designed). OQ1–OQ8 resolvidas no DESIGN. Próximo passo → /build. | /design (Claude Sonnet 5) |
| 2026-09-03 | 1.2 | Cascata da descoberta do recurso (`DISCOVERY_MVP_WALKING_SKELETON.md`), Modificadora. **A1/A2/A4/A6/A7 validadas** (A2/A4 com correção); **A9** nova. Métrica passa a `divida_consolidada` (bruta, PAF) — DV2. Grão anual `reference_year` + `DATE(ANO,12,31)` — DV1. Chave `UF` 2 letras → `uf_ibge` — DV3. Ajustados G1/G5/G9, S2/S7, AT1/AT3/AT4/AT5/AT7/AT9/AT10, C8/C9, §8, §10, §12. Status `✅ Complete (Designed)` mantido (correção factual, não re-escopo). | /iterate (Claude Sonnet 5) |
| 2026-09-03 | 1.3 | Correção factual encontrada ao escrever o código: **Brasil tem 26 estados + DF = 27** entes, não 28. Ajustados S2, §8 A4, §10 (volume + completude), §11. Contrato `divida_consolidada_estados.yaml` e `uf_ibge.csv` já corretos (27). | /build (Claude Sonnet 5) |
| 2026-09-03 | 1.4 | Shipped e arquivado. | /ship (Claude Sonnet 5) |
