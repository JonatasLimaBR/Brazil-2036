# DEFINE — CI_ASSURANCE_GATES

## Metadados

- **Feature:** CI_ASSURANCE_GATES
- **Status:** ✅ Shipped
- **Fase:** 1 (Define)
- **Entrada:** requisito direto — `VERIFY_SPEC_MVP_WALKING_SKELETON` achado #7 + AT11 PARTIAL; `SPEC-031`; `SHIPPED_2026-09-03 §7` (follow-ups de alta prioridade)
- **Criado:** 2026-09-04
- **Idioma:** PT-BR
- **Clarity score:** 14/15 (HIGH)
- **Branch:** `feature/ci-assurance-gates`
- **Design:** `.claude/sdd/features/DESIGN_CI_ASSURANCE_GATES.md` (2026-09-04)
- **Próximo passo:** `/build .claude/sdd/features/DESIGN_CI_ASSURANCE_GATES.md`

> Nota: assets do plugin SDD ausentes — documento segue a lista de seções obrigatórias do
> skill `sdd-define`; contract gate (`spec-lint`) não executável.

---

## 1. Problem statement

O CI não é um gate de merge confiável: `SPEC-031` / ADR-038 exigem que todo merge em `main`
seja bloqueado por format/lint/typecheck/unit/**integration**/contracts/security/**terraform**/
**spec-verify** verdes, mas hoje (a) não há teste de **integração** em tempo de PR — os testes do
pipeline usam fakes em memória e o BigQuery real só é tocado pelo `verify_chain.py` **depois** do
deploy na `main`; (b) não há **gate de spec-verifier** automatizado em nenhum workflow; (c) os
workflows são filtrados por path, então nenhum PR exercita o conjunto completo e os jobs de check
**não podem sequer ser required** (um PR que não toca o path deixa o check pendente "Expected"
para sempre).

---

## 2. Target users

| Persona | Descrição | Pain point |
|---|---|---|
| **Time de implementação / agentes de código** (primária) | Quem abre e faz merge de PR | Precisa de um verde confiável antes do merge; hoje um contrato quebrado ou um teste vermelho pode entrar na `main` porque o gate não roda naquele PR. |
| **Revisor independente do `/verify-spec`** (secundária) | Sessão nova read-only | Faz à mão verificações objetivas (arquivo existe? endpoint responde? campo no schema?) que um `spec-verify` automatizado poderia dar de piso. |
| **Mantenedor do repo / branch protection** (secundária) | Configura os required checks | Precisa de required checks que **resolvam sempre** (verde ou vermelho), sem travar PRs filtrados por path. |

---

## 3. Goals (MoSCoW)

### MUST
- **G1.** `data-checks`, `api-web-checks` e `terraform` (infra) **rodam em todo PR para `main` e todo push em `main`** — *pass-through* (verde, rápido) quando o próprio path não foi tocado; execução real quando foi — para poderem ser **required status checks** sem deadlock.
- **G2.** Gate de **integração em tempo de PR**: exercita o pipeline de ingestão contra um **dataset BigQuery de teste isolado** (`br2036_citest_<run_id>`), não fakes — cobre AT1/AT3/AT4/AT5/AT6/AT7/S7 do SPEC-033. Autentica por WIF. **Derruba** o dataset de teste ao fim (mesmo em falha).
- **G3.** Gate de **spec-verifier automatizado**: um script lê a lista de MUST de um SPEC + os IDs de acceptance test e checa mecanicamente os itens objetivamente verificáveis (arquivo/deliverable existe, endpoint responde, campo presente no schema, threshold presente no contrato), emitindo PASS/FAIL por item e exit ≠ 0 em qualquer FAIL. **Não substitui** o `/verify-spec` humano — é o piso.
- **G4.** `required_status_checks` da proteção de branch passa a incluir `secret-scan`, `data-checks`, `api-web-checks`, `terraform`, `integration`, `spec-verify`.
- **G5.** `agent-eval` declarado **N/A de forma legível por máquina** (arquivo `ci/gates.yaml` ou equivalente) com o motivo ("nenhum comportamento de agente em escopo") — satisfaz `SPEC-031` "agent evals when affected" de forma visível, não por ausência (ADR-036).

### SHOULD
- **G6.** O gate de integração degrada com clareza em **PR de fork** (sem OIDC/secrets por design do GitHub): mensagem "integration skipped: no GCP credentials on fork PR" e job neutro/verde — mas **obrigatório e real** em PR do mesmo repo e na `main`. Sem `pull_request_target`.
- **G7.** Job `ci-summary` que depende de todos os jobs de gate e serve como **o** required check (config de branch protection mais simples).

### COULD
- **G8.** Guarda de custo: uso de BQ do teste com cap de bytes e `default_table_expiration` no dataset de teste (R-012).
- **G9.** `spec-verify` roda contra qualquer `docs/specs/SPEC-*.md` que tenha um `spec-checks/SPEC-XXX.yaml` (extensível para a fatia #2).

---

## 4. Success criteria (mensuráveis)

| # | Critério | Medição |
|---|---|---|
| S1 | Pass-through é rápido | PR tocando só `docs/**` → `data-checks`, `api-web-checks`, `terraform`, `integration`, `spec-verify` **verdes em < 90 s cada**, e o PR faz merge. |
| S2 | Contrato quebrado é pego | PR que remove uma coluna obrigatória de `divida_consolidada_estados.yaml` (ou faz a Silver perder linhas) → job `integration` **vermelho** → merge bloqueado. |
| S3 | Deliverable de SPEC ausente é pego | PR que apaga `api/scripts/export_openapi.py` (ou `openapi/openapi.json`) → `spec-verify` **vermelho** contra SPEC-033. |
| S4 | Zero check pendente | 100% dos required checks resolvem (verde/vermelho) em **todo** PR — nenhum "Expected — waiting". |
| S5 | Sem dataset órfão | Após 3 execuções consecutivas de `integration` (pass ou fail), `bq ls` não mostra nenhum `br2036_citest_*`. |
| S6 | Proteção efetiva | `required_status_checks` lista ≥ 5 contextos; PR com qualquer um vermelho não é mergeável (`mergeable_state = blocked`). |
| S7 | Terraform real no PR | `terraform validate` + `plan` (via WIF, read-only) rodam em todo PR que toca `infra/**` e passam-through nos demais. |

---

## 5. Acceptance tests

- **AT1 — pass-through.** *Given* um PR que muda só `README.md`, *When* o CI roda, *Then* `data-checks`/`api-web-checks`/`terraform`/`integration`/`spec-verify` completam verdes em < 90 s sem tocar o GCP.
- **AT2 — execução real.** *Given* um PR que muda `ingestion/src/**`, *When* o CI roda, *Then* `data-checks` roda ruff+mypy+pytest de verdade e `integration` cria um dataset BQ de teste, roda o pipeline contra ele, afirma 27 linhas / cobertura de provenance, e derruba o dataset.
- **AT3 — contrato.** *Given* um PR que altera `contracts/divida_consolidada_estados.yaml` para exigir coluna inexistente, *When* `integration` roda, *Then* falha com a violação de contrato e o PR não é mergeável.
- **AT4 — deliverable de SPEC.** *Given* um PR que apaga `api/openapi/openapi.json`, *When* `spec-verify` roda contra SPEC-033, *Then* reporta FAIL no MUST "OpenAPI gerado" e sai ≠ 0.
- **AT5 — sem órfão.** *Given* 3 execuções seguidas de `integration`, *When* terminam (pass ou fail), *Then* `bq ls` não mostra `br2036_citest_*` (teardown em passo `always()`).
- **AT6 — WIF only + fork.** *Given* o job `integration`, *When* autentica no GCP, *Then* usa `google-github-actions/auth@v2` + provider WIF, sem chave estática; PR de fork sem OIDC → "integration skipped: no GCP credentials on fork PR" e job neutro/verde; PR do mesmo repo e `main` → execução real obrigatória.
- **AT7 — branch protection.** *Given* a proteção de branch, *When* consulto `required_status_checks`, *Then* contém `secret-scan`, `data-checks`, `api-web-checks`, `terraform`, `integration`, `spec-verify` (ou só `ci-summary` se G7).
- **AT8 — falha bloqueia.** *Given* um PR com `data-checks` vermelho, *When* tento fazer merge, *Then* o GitHub bloqueia (`mergeable_state = blocked`).
- **AT9 — agent-eval N/A visível.** *Given* o repo, *When* inspeciono a config de CI, *Then* `agent-eval` está declarado N/A com o motivo — não apenas ausente.

---

## 6. Out of scope

| Item | Motivo | Destino |
|---|---|---|
| Fatia #2 (INSS) | feature separada | `/brainstorm` próprio |
| **Emulador** de BigQuery | rejeitado — cobertura parcial de SQL; usamos dataset real isolado | — |
| Framework de contrato completo (Great Expectations / Soda) | `SPEC-005` próprio; aqui basta o check Python mínimo já existente | `SPEC-005` |
| Implementação de `agent-eval` | não há comportamento de agente ainda (ADR-036 é sobre *quando* houver) | quando entrar agente |
| Mudança no gating de **deploy** | deploy segue `main`-only pós-merge; esta feature é sobre o gate de **merge** | — |
| Merge queue / linear history | já configurados | — |
| CI multi-ambiente (stg/prod) | só dev nesta fase | fases de escala |
| Testes de carga/performance | fora de escopo | — |
| `spec-verify` como revisor semântico (substituir o humano) | é piso mecânico, não juízo | `/verify-spec` humano continua obrigatório |

---

## 7. Constraints

- **C1.** WIF only, sem chave estática (ADR-040).
- **C2.** Não enfraquecer gates existentes — `SPEC-031`: "warning-only replacements are not acceptable for critical gates".
- **C3.** O teste de integração **nunca** toca os datasets de produção (`br2036_bronze/silver/gold`); só `br2036_citest_*`.
- **C4.** Reusar a SA `tf-deployer` (já tem `bigquery.admin` — cria/derruba dataset); **sem novo grant amplo**.
- **C5.** PR de fork não recebe OIDC/secrets (design do GitHub) — degradar com clareza (G6/AT6) sem abrir buraco (nada de `pull_request_target`).
- **C6.** Custo do BQ de integração limitado (R-012); dataset de teste com TTL / `default_table_expiration`.
- **C7.** Todo merge em `main` é via PR (branch protection ligada em 2026-09-04).
- **C8.** Só `.github/workflows/` + helpers em `scripts/`; nenhum serviço novo.

---

## 8. Assumptions / risk register

| ID | Afirmação | Impacto se falsa | Validada |
|---|---|---|---|
| A1 | Um trigger `pull_request` **sem** `paths` num job que decide real-vs-pass-through por `git diff` é padrão viável no Actions | usar `dorny/paths-filter` ou um job stub sempre-verde | ☐ |
| A2 | WIF pode ser assumido por workflow de `pull_request` do **mesmo repo** (não fork) | gate de integração só na `main` push, cobertura de PR fraca | ☐ (GitHub dá OIDC a PR do mesmo repo — confirmar) |
| A3 | Um run real de integração (cria dataset → roda pipeline/SQL → afirma → derruba) cabe em < 5 min e centavos | PRs lentos/caros; mitigar rodando o SQL direto, sem build+deploy do container | ☐ |
| A4 | O pipeline aceita um **prefixo/override de dataset** via `config.yaml`/env | pequena mudança em `config.py`/`pipeline.run()` para aceitar override | ☐ (hoje só `GCP_PROJECT`/`RAW_BUCKET` por env) |
| A5 | `spec-verify` cabe em ~150 linhas Python + um `spec-checks/SPEC-033.yaml` | escopo cresce; fallback = script de checklist mantido à mão | ☐ |
| A6 | Tornar `data-checks`/etc. sempre-verde não aumenta custo/minutos de forma relevante | custo menor, aceito | ☐ |

---

## 9. Technical context

| Aspecto | Definição |
|---|---|
| **Onde vive** | `.github/workflows/*.yml` (reestrutura `data.yml`, `api-web.yml`, `infra.yml`; possível `ci.yml` guarda-chuva), `scripts/spec_verify.py`, `scripts/ci/**` (helpers de pass-through / teardown), `ingestion/tests/integration/**` (teste de BQ real + fixture), possível `spec-checks/SPEC-033.yaml`. |
| **Impacto IaC** | Mínimo. Talvez `default_table_expiration` como convenção no dataset de teste (criado pelo próprio job via `bq`, não Terraform). Grants de `tf-deployer` inalterados (já `bigquery.admin`). |
| **Domínios de KB** | `SPEC-031` (CI bloqueante), `SPEC-033` (o que verificar), `SPEC-005` (contratos), ADR-036 (agent evals), ADR-038 (main protegida), ADR-040 (WIF); `RISK-CONTROL-TEST-MATRIX` (R-006, R-011, R-012); `docs/discovery/05-ASSURANCE-MATRIX.md`. |

---

## 10. Data contract (aplicável — teste de integração)

### Source inventory
- **Fixture commitada:** `ingestion/tests/integration/fixtures/divida_sample.csv` (~5 linhas: 2 UF × 2 anos + DF), formato idêntico ao real (`UF;ANO;VALOR`, `;`, decimal `,`, UTF-8). Determinística, sem rede. *(Fork de design OQ1: fixture vs fetch real do Tesouro — lean fixture; fetch real num job noturno separado.)*

### Volumes
- ~5 linhas. Dataset de teste `br2036_citest_<run_id>` com as 4 tabelas de camada + provenance + `uf_ibge`.

### Freshness SLA
- N/A (teste).

### Schema contract
- O mesmo `divida_consolidada_estados.yaml` v1. O teste afirma que as regras (schema Bronze, 27 entes na Gold — **ajustado para a contagem da fixture** —, `value >= 0`, NOT NULL em PK, cobertura de provenance) são avaliadas e barram quando violadas.

### Completeness metrics
- Para a fixture: todas as UF da fixture presentes na Gold para o `MAX(reference_year)` da fixture; zero nulo em PK; cobertura de provenance 100%.
- **Nota:** o check de "27 entes" do contrato de produção é parametrizado para a contagem da fixture no run de integração (senão a fixture nunca passaria) — o contrato de produção continua exigindo 27 no `verify_chain.py` da `main`.

### Lineage requirements
- O teste verifica que a cadeia `dataset_registry → GCS RAW (uri) → Bronze (_row_hash) → Silver → Gold → metric_provenance` fecha para pelo menos uma UF da fixture (S7 do SPEC-033, agora em tempo de PR).

---

## 11. Clarity score breakdown

| Elemento | Nota | Máx | Observação |
|---|---|---|---|
| Problem | 3 | 3 | 3 lacunas concretas nomeadas (integração / spec-verify / path filters). |
| Users | 2 | 3 | Time + revisor + mantenedor; "usuário de um gate de CI" é parcialmente abstrato. |
| Goals | 3 | 3 | 5 MUST, 2 SHOULD, 2 COULD; mensuráveis. |
| Success | 3 | 3 | S1–S7 com números/thresholds (< 90 s, ≥ 5 contextos, 0 órfão, 3 runs). |
| Scope | 3 | 3 | Out-of-scope grande e explícito (emulador rejeitado, agent-eval, deploy gating, etc.). |
| **Total** | **14** | **15** | **HIGH — prosseguir para `/design`.** |

---

## 12. Open questions

| ID | Questão | Resolver em |
|---|---|---|
| OQ1 | Dado do teste de integração: fixture commitada (determinística) vs fetch real do Tesouro (real). Lean fixture; fetch real num job noturno. | `/design` |
| OQ2 | `spec-verify`: script genérico + `spec-checks/SPEC-XXX.yaml` por SPEC, vs script bespoke por SPEC. Lean genérico + yaml. | `/design` |
| OQ3 | Um `ci.yml` guarda-chuva com todos os jobs vs manter 3 workflows + job agregador `ci-summary`. | `/design` |
| OQ4 | O pipeline precisa de parâmetro de prefixo de dataset (A4)? Confirmar e desenhar o override. | `/design` |
| OQ5 | Mecanismo de pass-through: `dorny/paths-filter` vs `git diff` num step vs `paths` no job + stub irmão. | `/design` |
| OQ6 | `integration` cobre também a API (subir uvicorn contra a Gold de teste + curl) ou só o pipeline? Lean só pipeline nesta rodada. | `/design` |
| OQ7 | `required_status_checks`: listar os 6 contextos ou só `ci-summary` (G7)? | `/design` + config de branch protection |

---

## 13. Revision history

| Data | Versão | Mudança | Autor |
|---|---|---|---|
| 2026-09-04 | 1.0 | Criação a partir do achado #7 do `/verify-spec`, `SPEC-031`, `SHIPPED §7`. Clarity 14/15. Status → Ready for Design. Branch `feature/ci-assurance-gates`. | /define (Claude Sonnet 5) |
| 2026-09-04 | 1.1 | Fase 2 concluída. D1–D6 (D1→ADR-054); manifesto de 22 itens. Status → ✅ Complete (Designed). | /design (Claude Sonnet 5) |
| 2026-09-04 | 1.2 | Build concluída. Verificação local verde; prova do CI pendente do PR. Status → ✅ Complete (Built). | /build (Claude Sonnet 5) |
| 2026-09-04 | 1.3 | `/verify-spec` independente = OVERALL PASS. PR #1 merged em `main` (squash). Shipped e arquivado. | /ship (Claude Sonnet 5) |
