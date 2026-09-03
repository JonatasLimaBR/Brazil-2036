# BUILD REPORT — MVP_WALKING_SKELETON

## Metadados

- **Feature:** MVP_WALKING_SKELETON
- **Fase:** 3 (Build) — **concluída** (PR1 + PR2 verdes no GCP real)
- **Entrada:** `.claude/sdd/features/DESIGN_MVP_WALKING_SKELETON.md` (v1.2)
- **Data:** 2026-09-03
- **Status da build:** ✅ **Complete (Built)** — cadeia provada ponta a ponta em `brasil2036-dev`
- **Ambiente vivo:**
  - Web (card público): `https://br2036-web-gzt6fzwoda-rj.a.run.app`
  - API: `https://br2036-api-gzt6fzwoda-rj.a.run.app` (`/v1/metrics/{id}`, `/v1/provenance/{id}`, `/openapi.json`)
- **Próximo passo:** `/verify-spec` (SPEC-033, sessão nova read-only) → `/ship`

### Incrementos
| # | Escopo | Verificação |
|---|---|---|
| A | Bloco de docs (manifesto 1–3): ADR-051, ADR-052, SPEC-033, INDEX.md | inspeção estrutural |
| B | Tarefa 1 do PR1: descoberta do recurso → `DISCOVERY_*.md`; cascata DV1–DV3 (`/iterate`) | — |
| C | Fatia do PR1 sem dependência de GCP: reference data, contrato v1, connector HTTP + parsing, modelos SQL, testes | ✅ `ruff` + `mypy --strict` + `pytest` (30) via `uv` |
| D | PR1 completo em modelo GitOps/WIF: módulos GCP, `Dockerfile`, `verify_chain.py`, `bootstrap.sh`, `infra/terraform/**`, workflows `infra.yml` + `data.yml` | ✅ `ruff` + `mypy --strict` (15) + `pytest` (44) + `terraform validate` |
| E | **PR1 executado no GCP real**: `bootstrap.sh` rodado, WIF federado, Actions Variables setadas; `infra` verde; `data` verde → job baixou a Dívida real, RAW→Bronze→Silver→Gold→provenance, `verify_chain.py` PASS | ✅ **27 entes / 2022 / 100% cobertura de provenance** no BigQuery |
| F | **PR2**: `api/` (FastAPI, `/v1/metrics` + `/v1/provenance`, OpenAPI gerado), `web/` (Vite+TS, 1 card, cliente gerado), Terraform da SA `api-runtime`, `.github/workflows/api-web.yml` | ✅ `ruff`+`mypy`+`pytest` (api, 9) + `tsc`+`vite build` (web) + **Playwright e2e contra a URL viva** |

> Escopo desta execução: apenas os itens 1–3 do manifesto (documentos que destravam D2/D5/D6).
> Decisão de escopo dirigida pelo usuário e pelas restrições de ambiente — ver Autonomous Decisions #2.
> Assets do plugin SDD ausentes (`BUILD_REPORT_TEMPLATE.md`, `kb/`, `agents/**`); relatório segue
> a lista de seções do skill `sdd-build`.

---

## 1. Task execution

| # | Arquivo | Ação | Agente | Verificação | Resultado |
|---|---|---|---|---|---|
| 1 | `docs/adrs/ADR-051-frontend-stack-vite-typescript-for-public-landing.md` | Create | `architect` → `(direct)` | Conformidade com template ADR-001..050 (Status/Contexto/Decision drivers/Alternativas/Decisão/Por que/Consequências/Verificação/Quando reconsiderar) | ✅ |
| 2 | `docs/adrs/ADR-052-sql-execution-for-walking-skeleton-refines-adr-007.md` | Create *(reinterpretado — ver AD #1)* | `architect` → `(direct)` | Idem template; declara "refina, não substitui ADR-007" | ✅ |
| 3 | `docs/specs/SPEC-033-MVP-WALKING-SKELETON.md` | Create | `architect` → `(direct)` | Estilo enxuto de SPEC-001..032; MUST PR1 / MUST PR2 / Deliverables / Acceptance / Future work; rastreabilidade R1–R14 / AT1–AT11 | ✅ |
| + | `INDEX.md` | Modify | `(direct)` | 3 entradas novas na ordem correta (ADR-051, ADR-052, SPEC-033) | ✅ |

Delegação via Task tool: **nenhuma** — os 3 arquivos são documentos de arquitetura; `architect`
não é agente com ferramenta de escrita neste ambiente, então execução direta a partir dos
padrões do DESIGN (§3 D2/D5/D6) e do template ADR observado no repo.

### Incremento C — fatia do PR1 sem GCP (manifesto: 12,13,14,15,19,20,21,22,23 parciais + testes 26/28/parte de 29/30)

| Arquivo | Ação | Agente | Nota |
|---|---|---|---|
| `.gitattributes` | Create | `(direct)` | `* text=auto eol=lf` — encerra os avisos LF/CRLF |
| `ingestion/pyproject.toml` | Create | `(direct)` | deps + ruff/mypy strict/pytest; build hatchling |
| `ingestion/reference/uf_ibge.csv` | Create | `(direct)` | 27 linhas (26 estados + DF), `uf,state_ibge_code,state_name` |
| `ingestion/contracts/divida_consolidada_estados.yaml` | Create | `(direct)` | contrato v1 (formato real, `keys=[state_ibge_code,reference_year]`, `= 27`) |
| `ingestion/src/ingestion/{__init__,config}.py/.yaml` | Create | `(direct)` | config: `resource_url`, `metric_id='divida_consolidada'`, nomes de tabela, `gcp_project=""` |
| `ingestion/src/ingestion/connectors/base.py` | Create | `ai-data-engineer-gcp` → `(direct)` | interface SPEC-003 (`Protocol`), `ResourceRef`, `DownloadResult`, `retry_with_backoff[T]` |
| `ingestion/src/ingestion/connectors/divida_estados.py` | Create | `ai-data-engineer-gcp` → `(direct)` | connector CKAN: HEAD/GET com retry, `validate` do header `UF;ANO;VALOR`, `checkpoint` por hash; sessão HTTP injetável |
| `ingestion/src/ingestion/parsing.py` | Create | `(direct)` | `parse_brl_number` (milhar `.`, decimal `,`), `parse_year`, `reference_date_for_year` = `DATE(y,12,31)` |
| `ingestion/src/ingestion/contract.py` | Create | `data-quality-analyst` → `(direct)` | loader do YAML; `check_bronze_schema`, `check_gold` (funções puras sobre estruturas — sem cliente BQ) |
| `ingestion/sql/silver/debt_state.sql` | Create | `sql-optimizer` → `(direct)` | formato Dataform; `UF`→IBGE join, `DATE(ANO,12,31)`, `REPLACE` pt-BR → NUMERIC |
| `ingestion/sql/gold/gold_debt_state_current.sql` | Create | `sql-optimizer` → `(direct)` | `MERGE` por `(state_ibge_code, reference_year, metric_id)` |
| `ingestion/tests/test_parsing.py` | Create | `(direct)` | 9 casos — parsing e data |
| `ingestion/tests/test_connector.py` | Create | `python-reviewer` → `(direct)` | 7 casos — download/retry/validate/checkpoint com `FakeSession` |
| `ingestion/tests/test_contract.py` | Create | `data-quality-analyst` → `(direct)` | 10 casos — bronze schema + gold rules (27 entes, negativos, cobertura provenance) |
| `ingestion/README.md` | Create | `code-documenter` → `(direct)` | layout + o que falta (P2/P4) |
| `.github/workflows/security.yml` | Create | `security-reviewer` → `(direct)` | gitleaks em PR/push (R-011) — não precisa de GCP/WIF |

**Não implementado** (precisa de projeto GCP + WIF — P2/P4): `raw.py`, `bronze.py`, `registry.py`,
`provenance.py`, `pipeline.py`, `infra/terraform/**`, `.github/workflows/data.yml`; e todo o PR2.

---

## 2. Verification results

| Check | Comando | Resultado | Nota |
|---|---|---|---|
| Estrutura ADR | inspeção vs. ADR-005/007/024/028/044 | ✅ | mesmo conjunto de seções e ordem |
| Estrutura SPEC | inspeção vs. SPEC-001 | ✅ | MUST / Deliverables / Acceptance preservados; seções extra (split PR, Future work) aditivas |
| Referências cruzadas | grep de IDs citados | ✅ | ADR-011/012/024/028/039/040/044/052, SPEC-001/002/003/004/005/007/026/031, DEFINE/DESIGN — todos existem |
| Lint (incremento C) | `uv run --with ruff ruff check .` | ✅ | All checks passed |
| Types (incremento C) | `uv run --with mypy … mypy` (`strict`) | ✅ | Success: no issues found in 6 source files |
| Testes (incremento C) | `uv run --with pytest … python -m pytest -q` | ✅ | 30 passed |
| Não-silêncio sobre ADR-007 | leitura de `ADR-007` | ✅ | `ADR-007` **não foi editado**; ADR-052 declara o relacionamento explicitamente |
| Lint/types/tests | n/a | — | bloco só de docs; sem código |
| Segredos | grep | ✅ | nenhum |
| TODOs | grep | ✅ | nenhum |

---

## 3. Autonomous Decisions

| # | Decision Point | Options Considered | Chose | Rationale |
|---|---|---|---|---|
| 1 | Manifesto item 2 era "Modify `ADR-007` in place (nota de amendment)" | (a) editar ADR-007 adicionando seção "Amendment"; (b) criar ADR novo que refina ADR-007 e deixar ADR-007 intocado | (b) — **ADR-052** como ADR de refinação | `CLAUDE.md` (não-negociável): "Never replace an ADR silently; supersede it with another ADR." Edição in-place pode ler como mudança silenciosa. ADR-052 datado, com escopo explícito e frase "refina, não substitui", é a forma auditável e conforme. É o menor desvio correto do DESIGN. |
| 2 | Escopo da build | (a) 56 arquivos completos; (b) só docs (1–3); (c) docs + PR1 | (b) | Usuário pediu "a melhor abordagem" após ser oferecido full/docs/PR1. PR1 não pode ficar verde nesta sessão: sem projeto GCP/billing (DEFINE A3 não validada), sem baseline `git`, sem CI/WIF, sem a URL real do recurso no dados.gov.br (tarefa 1 / A1/A2). D1 e Abordagem B pedem PRs incrementais e revisáveis. Build completa numa tacada contraria o processo PR-based com autor/revisor separados. |
| 3 | Idioma do SPEC-033 | (a) PT-BR (CONTEXTO §23 diz PRD/ADR/SPEC em PT-BR); (b) inglês enxuto | (b) inglês | Os 32 SPECs existentes (SPEC-001..032) estão em inglês, apesar do CONTEXTO §23. Consistência com os arquivos reais do repo pesa mais que a diretriz não aplicada. ADRs 051/052 mantiveram o template PT dos ADR-001..050. |
| 4 | `ADR-051` "Alternativas consideradas" com A/B/C/D | (a) truncar em 3 como o template; (b) listar as 4 reais (no-build, Next, Astro, Vite) | (b) 4 opções | Havia 4 alternativas genuínas; truncar dropava uma real. Desvio cosmético do template. |
| 5 | `MANIFEST.json` (manifesto de integridade sha256) | (a) regenerar hashes à mão para os arquivos novos/alterados; (b) deixar stale e registrar follow-up | (b) | `MANIFEST.json` é artefato gerado; recalcular hash à mão é propenso a erro e fora do escopo de uma tarefa de docs. Registrado como blocker de follow-up. |
| 6 | Escopo do incremento C | (a) esperar P2/P4 e fazer o PR1 inteiro; (b) escrever agora só a fatia do PR1 que roda e se verifica sem GCP | (b) | `uv` disponível ⇒ `ruff`/`mypy`/`pytest` locais. connector HTTP, parsing, contrato, SQL e testes não precisam de GCP e ficam verificados de verdade; os módulos GCP-bound continuam pendentes de P2/P4. Progresso real sem código especulativo. |
| 7 | Contagem de entes federativos | (a) manter "27 estados + DF = 28" dos docs; (b) corrigir para "26 estados + DF = 27" | (b) | O Brasil tem **26 estados** + Distrito Federal. Erro herdado do DEFINE original, propagado a DESIGN/SPEC-033/DISCOVERY. `uf_ibge.csv` (27 linhas) e o contrato (`= 27`) já foram escritos corretos. Correção factual aplicada a DEFINE v1.3, DESIGN v1.2, SPEC-033, DISCOVERY. |
| 8 | Provisionamento GCP (pedido do usuário: "a partir do git, criar recursos pela federação") | (a) `terraform apply` local pelo humano; (b) GitOps — Actions roda `terraform` via WIF | (b) | Pedido explícito. Projeto + billing + o próprio pool WIF + bucket de state não podem nascer da federação (não há identidade ainda) → `scripts/bootstrap.sh` roda uma vez à mão. Todo o resto vem de `infra.yml` (Actions + `google-github-actions/auth@v2` + WIF, sem chave). `data.yml` faz build/push da imagem e executa o Cloud Run Job, depois `verify_chain.py`. |
| 9 | Escopo de roles do `tf-deployer` no bootstrap | (a) `roles/owner`; (b) conjunto de admin por serviço | (b) | Menos privilégio que `owner`. `billing.projectManager` removido (inválido em escopo de projeto); `serviceaccount.user` → `iam.serviceAccountUser` (bug de nome). |
| 10 | Falhas de runtime resolvidas ao executar no GCP (não são forks de design; correções de implementação) | — | — | (a) Cloud Build sem `cloudbuild.builds.editor` → build via `docker` no runner + push direto ao Artifact Registry. (b) `UPDATE/DELETE over streaming buffer` → trocar `insert_rows_json` por DML, e depois por **`CREATE OR REPLACE TABLE ... AS SELECT`** (zero DML, imune ao buffer) em `registry`/`provenance`/`bronze`/gold SQL. (c) `MERGE` exige tabela pré-existente → gold vira `CREATE OR REPLACE`. (d) Cloud Run Job/Services exigem imagem existente → imagem placeholder pública + `ignore_changes=[image]`; o workflow troca pela real. (e) `account_id` de SA ≥ 6 chars → `api` → `api-runtime`. (f) corrida entre `infra` e `api-web` → `api-web` faz poll da SA antes do deploy. (g) fetch cross-origin bloqueado → `CORSMiddleware(allow_origins=['*'], GET)` na API (pública, ADR-044). |

---

## 4. Blockers e trabalho restante

### Concluído

- **PR1 + PR2 verdes no GCP real.** Ambiente vivo (Cloud Run, `southamerica-east1`):
  - web: `https://br2036-web-gzt6fzwoda-rj.a.run.app`
  - api: `https://br2036-api-gzt6fzwoda-rj.a.run.app`
- Prova no BigQuery: 27 entes / `reference_year=2022` / cobertura de provenance 100%;
  `/v1/provenance/divida_consolidada` resolve a cadeia `SPEC-007` completa; nenhum
  número no bundle do web (checado no e2e).

### Follow-ups (não bloqueiam a feature)

- **Proteção de branch `main` + fluxo de PR** — deferido pelo usuário para "depois do PR2" (agora due). SPEC-032 / ADR-038.
- `MANIFEST.json` desatualizado (P6) — script de regeneração.
- URL do catálogo dados.gov.br para `dataset_registry.source_url` (P7 / OQ9) — relevante para a submissão CGU.
- Times/handles de `CODEOWNERS` (P5).
- Provenance histórica (hoje `CREATE OR REPLACE` guarda só o último ano) — `SPEC-006`/incremento.
- Node20-deprecation warnings nos workflows (cosmético).

### (histórico) Código do PR1 — completo e verificado localmente
`ingestion/**` (connector, parsing, raw, bronze, silver/gold SQL, registry, provenance, contract,
pipeline, `__main__`, `Dockerfile`, `verify_chain.py`), `infra/terraform/**`, `scripts/bootstrap.sh`,
`.github/workflows/{infra,data,security}.yml`. 44 testes; `mypy --strict`; `terraform validate`.
**Falta apenas rodar em GCP real** (nenhuma execução de infra/integração é possível sem projeto).

### Pré-requisitos para EXECUTAR o PR1 em GCP
| ID | Pendência | Como | Status |
|---|---|---|---|
| P1 | Repo remoto | `github.com/JonatasLimaBR/Brazil-2036`, `origin/main` | ✅ feito |
| P2 | Projeto GCP dev + billing + bootstrap (bucket state, pool WIF, `tf-deployer` SA) | rodar `scripts/bootstrap.sh` com `PROJECT_ID`/`REGION`/`BILLING_ACCOUNT`/`GITHUB_REPO` | ⏳ **você** |
| P3 | Descoberta do recurso | `DISCOVERY_*.md`; cascata DV1–DV3 | ✅ feito |
| P4 | WIF federado + variáveis de repo no GitHub | o `bootstrap.sh` cria o pool/provider e imprime `GCP_WIF_PROVIDER` / `GCP_DEPLOYER_SA` / `GCP_PROJECT` / `GCP_REGION` / `GCP_TF_STATE_BUCKET` — adicionar como **Actions Variables** | ⏳ **você** (depende de P2) |
| P5 | Times para `CODEOWNERS` | criar handles/teams e editar `.github/CODEOWNERS` | ⏳ pendente |
| P6 | Regenerar `MANIFEST.json` | script `scripts/gen_manifest.py` (a escrever) | ⏳ pendente |
| P7 | URL do catálogo dados.gov.br | preencher `config.yaml:catalog_url` e `contract:source.catalog_url` | ⏳ pendente (não bloqueia) |

### Fluxo após P2/P4
1. `git push` → workflow **infra** roda `terraform init/plan/apply` via WIF → cria bucket RAW, 4 datasets, Artifact Registry, Cloud Run Job, IAM, budget.
2. Workflow **data**: `checks` (ruff/mypy/pytest) → `deploy-and-run` (build+push imagem, `run jobs deploy`, `run jobs execute --wait`, `verify_chain.py`).
3. `verify_chain.py` falha o CI se a Gold não tiver 27 entes ou a cobertura de provenance quebrar.

### Decisão já resolvida (sem blocker)
- OQ1–OQ9: OQ1–OQ8 em `DESIGN §3` (ADR-051/052); OQ9 = P7.

---

## 5. Status transitions

Aplicadas ao concluir a build (PR1 + PR2 verdes no GCP real):

| Arquivo | Status | Próximo passo |
|---|---|---|
| `DEFINE_MVP_WALKING_SKELETON.md` | `✅ Complete (Built)` | `/verify-spec` → `/ship` |
| `DESIGN_MVP_WALKING_SKELETON.md` | `✅ Complete (Built)` | `/verify-spec` → `/ship` |

---

## 6. Handoff

**Build concluída.** Próximos passos:

1. `/verify-spec` contra `SPEC-033` em sessão nova, read-only — PASS/FAIL por requisito (PR1 + PR2).
2. Proteção de branch `main` + fluxo de PR (deferido pelo usuário para "depois do PR2").
3. `/ship` — arquiva a feature, lições aprendidas, status → Shipped.
4. Follow-ups da §4 (MANIFEST.json, URL do catálogo dados.gov.br para o concurso CGU, CODEOWNERS).

---

## 7. Quality gate (parcial)

- [x] Arquivos do escopo desta execução criados (1–3 + INDEX.md)
- [x] Cada arquivo verificado (estrutura, referências cruzadas, não-silêncio sobre ADR-007)
- [n/a] Validação full de lint/types/test — sem código neste bloco
- [x] Sem TODO
- [x] Sem segredo/credencial
- [x] Atribuição de agente registrada (§1)
- [x] Tabela de Autonomous Decisions preenchida (§3)
- [ ] DEFINE status → `✅ Complete (Built)` — **não**, build parcial
- [ ] DESIGN status → `✅ Complete (Built)` — **não**, build parcial
- [x] BUILD_REPORT gerado

---

## 8. Revision history

| Data | Versão | Mudança | Autor |
|---|---|---|---|
| 2026-09-03 | 0.1 | Execução parcial: bloco de docs (ADR-051, ADR-052, SPEC-033) + INDEX.md. PR1/PR2 pendentes. | /build (Claude Sonnet 5) |
| 2026-09-03 | 0.2 | Tarefa 1 do PR1 (descoberta do recurso) concluída → `DISCOVERY_MVP_WALKING_SKELETON.md`. Cascata DV1–DV3 (via `/iterate`) aplicada a DESIGN v1.1, DEFINE v1.2, SPEC-033. P1/P3 marcados feitos; P7 (URL catálogo) adicionado. | /build + /iterate (Claude Sonnet 5) |
| 2026-09-03 | 0.3 | Incremento C: fatia do PR1 sem GCP (16 arquivos em `ingestion/` + `.gitattributes` + `security.yml`). `ruff` + `mypy --strict` + `pytest` (30) verdes via `uv`. AD #6/#7. Correção "26 estados + DF = 27" (DEFINE v1.3, DESIGN v1.2, SPEC-033, DISCOVERY). | /build (Claude Sonnet 5) |
| 2026-09-03 | 0.4 | Incremento D: PR1 completo em modelo **GitOps/WIF** (pedido do usuário). Módulos GCP (`raw/bronze/registry/provenance/pipeline/__main__/bigquery_io/sql_render`), `Dockerfile`, `scripts/{bootstrap.sh,verify_chain.py}`, `infra/terraform/**`, workflows `infra.yml`+`data.yml`. `ruff` + `mypy --strict` (15) + `pytest` (44) + `terraform validate`/`fmt` verdes. AD #8/#9. Repo em `github.com/JonatasLimaBR/Brazil-2036`. | /build (Claude Sonnet 5) |
| 2026-09-03 | 1.0 | **Build concluída.** Incremento E: `bootstrap.sh` executado, WIF federado, 5 Actions Variables; `infra` + `data` verdes → job rodou no GCP real, `verify_chain.py` PASS (27 entes / 2022 / provenance 100%). Incremento F: PR2 (`api/` FastAPI + `web/` Vite+TS + `api-web.yml`), `deploy` + Playwright e2e verdes contra a URL viva. 7 falhas de runtime corrigidas (AD #10). DEFINE/DESIGN → `✅ Complete (Built)`. Próximo: `/verify-spec` → proteção de branch → `/ship`. | /build (Claude Sonnet 5) |
