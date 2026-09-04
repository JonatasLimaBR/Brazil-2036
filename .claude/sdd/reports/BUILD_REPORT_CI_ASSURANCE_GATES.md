# BUILD REPORT — CI_ASSURANCE_GATES

## Metadados

- **Feature:** CI_ASSURANCE_GATES
- **Fase:** 3 (Build)
- **Entrada:** `.claude/sdd/features/DESIGN_CI_ASSURANCE_GATES.md` (v1.0)
- **Branch:** `feature/ci-assurance-gates`
- **Data:** 2026-09-04
- **Status da build:** ✅ Complete (Built) — verificado localmente; a prova final é o primeiro run do `ci.yml` no PR.
- **Próximo passo:** abrir PR → `ci.yml` verde → trocar required check para `ci-gate` → `/verify-spec` → `/ship`.

> Assets do plugin SDD ausentes — relatório segue a lista de seções do skill `sdd-build`.

---

## 1. Task execution

| # | Arquivo | Ação | Agente | Nota |
|---|---|---|---|---|
| 1 | `docs/adrs/ADR-054-ci-merge-gate-umbrella.md` | Create | `architect`→`(direct)` | D1: `ci.yml` + `ci-gate` como único required check |
| 2 | `.github/ci/gates.yaml` | Create | `(direct)` | manifesto SPEC-031→job/status; `agent-eval: n/a` + motivo |
| 3 | `spec-checks/SPEC-033.yaml` | Create | `(direct)` | asserções checáveis do SPEC-033 |
| 4 | `scripts/spec_verify.py` | Create | `python-developer`→`(direct)` | verificador genérico; 6 tipos de check; `os.walk` com prune |
| 5 | `scripts/pyproject.toml` | Create *(AD #1)* | `(direct)` | manifesto Python de `scripts/` (uv/ruff/mypy/pytest) |
| 6 | `scripts/tests/test_spec_verify.py` | Create | `python-developer`→`(direct)` | 8 testes (cada tipo: PASS + FAIL; agent-eval sem reason falha) |
| 7 | `ingestion/src/ingestion/config.py` | Modify | `python-developer`→`(direct)` | env overrides: `RESOURCE_URL`, `RAW_PREFIX`, `BQ_DATASET_{CONTROL,BRONZE,SILVER,GOLD}` |
| 8 | `ingestion/src/ingestion/connectors/divida_estados.py` | Modify | `ai-data-engineer-gcp`→`(direct)` | `file://` em `download()` (`_download_file`/`_download_http`) |
| 9 | `ingestion/tests/test_connector.py` | Modify | `python-reviewer`→`(direct)` | +`test_download_file_scheme_reads_local` (HTTP não tocado) |
| 10 | `ingestion/tests/integration/__init__.py` | Create | `(direct)` | pacote |
| 11 | `ingestion/tests/integration/fixtures/divida_sample.csv` | Create | `(direct)` | SP/RJ/DF × 2021/2022 (6 linhas) |
| 12 | `ingestion/tests/integration/fixtures/contract_fixture.yaml` | Create *(implícito no DESIGN §8)* | `data-contracts-engineer`→`(direct)` | contrato de fixture (`= 3` entes); produção intocado |
| 13 | `ingestion/tests/integration/test_pipeline_bigquery.py` | Create | `data-quality-analyst`→`(direct)` | `@pytest.mark.integration`; owns dataset lifecycle (AD #2); assert 3 linhas / provenance 100% / lineage fecha |
| 14 | `ingestion/pyproject.toml` | Modify | `(direct)` | `markers=[integration]`, `addopts='-m "not integration"'` |
| 15 | `ingestion/README.md` | Modify | `code-documenter`→`(direct)` | como rodar a integração local |
| 16 | `.github/workflows/ci.yml` | Create | `ci-cd-specialist`→`(direct)` | guarda-chuva: `changes` + 6 gates condicionais + `ci-gate` agregador |
| 17 | `.github/workflows/data.yml` | Modify | `ci-cd-specialist`→`(direct)` | remove `data-checks`; só `deploy-and-run` (push→main) |
| 18 | `.github/workflows/api-web.yml` | Modify | `ci-cd-specialist`→`(direct)` | remove `api-web-checks`; só `deploy` |
| 19 | `.github/workflows/infra.yml` | Modify | `ci-cd-specialist`→`(direct)` | remove `pull_request`; só `apply` (push→main) |
| 20 | `.github/workflows/security.yml` | Delete *(AD #4)* | `security-reviewer`→`(direct)` | secret-scan vive no `ci.yml` |
| 21 | `.github/CODEOWNERS` | Modify | `(direct)` | `+/scripts/ +/.github/ +/spec-checks/` |
| 22 | `docs/specs/SPEC-031-CI-GATES.md` | Modify | `architect`→`(direct)` | seção "Realization (ADR-054)" |
| 23 | `docs/adrs/ADR-036-agent-evals-block-merge.md` | Modify | `architect`→`(direct)` | nota: N/A declarado em `gates.yaml` |
| 24 | `INDEX.md` | Modify | `(direct)` | +ADR-054, `gates.yaml`, `spec-checks/`, `spec_verify.py` |

Delegação via Task tool: nenhuma (agentes casados não têm ferramenta de escrita nesta sessão; execução direta a partir dos padrões §5 do DESIGN).

---

## 2. Verification results

| Check | Comando | Resultado |
|---|---|---|
| `scripts/` lint | `uv run ruff check .` + `ruff format --check .` | ✅ |
| `scripts/` types | `uv run mypy` | ✅ (1 arquivo) |
| `scripts/` unit | `uv run pytest -q` | ✅ 8 passed |
| `spec_verify` vs SPEC-033 real | `python spec_verify.py spec-checks/SPEC-033.yaml` | ✅ **PASS (31 checks)** |
| `ingestion/` lint+format | `ruff check` + `ruff format --check` | ✅ (após `ruff format` — AD #3) |
| `ingestion/` types | `mypy` | ✅ (15 arquivos) |
| `ingestion/` unit | `pytest -q` | ✅ 44 passed, 1 deselected (integração) |
| `api/` lint+format+types+unit | idem | ✅ (9 tests) |
| `terraform` | `terraform fmt` | ✅ |
| `ci.yml` YAML | inspeção (sem `actionlint` no ambiente) | ⚠️ validado por leitura; prova = 1º run no PR |
| `integration` job (BQ real) | — | ⚠️ não executável sem push (WIF só no CI); o teste coleta OK (`1 deselected`) |

---

## 3. Autonomous Decisions

| # | Decisão | Opções | Escolha | Racional |
|---|---|---|---|---|
| 1 | `scripts/` precisa de toolchain própria | (a) rodar `spec_verify` com `uv run --with pyyaml` ad-hoc; (b) `scripts/pyproject.toml` | (b) | Espelha `ingestion/`/`api/`: `uv sync --extra dev` + ruff/mypy/pytest padronizados; o job `lint-typecheck-unit` roda igual nos 3. |
| 2 | Ciclo de vida dos datasets `citest_*` | (a) `bq mk`/`bq rm` no workflow (como no DESIGN §5.3); (b) fixture pytest cria/derruba | (b) | Lógica num lugar só; roda idêntico local e no CI; teardown garantido por `finally` + TTL 1h + sweep de segurança no job. O workflow só seta env + roda `pytest -m integration`. |
| 3 | Gate `format` (`ruff format --check`) falhava em 9 arquivos pré-existentes | (a) tirar `ruff format` do gate; (b) `ruff format` no repo | (b) | `SPEC-031` lista "format" como gate. Reformatação é cosmética; testes reverificados verdes. |
| 4 | `security.yml` | (a) manter como fallback de push; (b) remover (secret-scan no `ci.yml`) | (b) | Evita gitleaks rodando 2×; `ci.yml` cobre PR e push. O contexto `secret-scan` continua existindo (job homônimo no `ci.yml`) → branch protection atual segue satisfeita até o flip para `ci-gate`. |
| 5 | `lint-typecheck-unit` condicional por área? | (a) 3 jobs condicionais (`ingestion`/`api`/`scripts`); (b) 1 job sempre, com passos sequenciais | (b) | ~1–2 min total; sempre reporta (bom para o agregador); menos YAML. Pass-through de verdade só nos jobs caros (`web`, `terraform`, `integration`). |
| 6 | `no_static_keys` do `spec_verify` acusava fixtures de teste | (a) marcador de allowlist; (b) podar `tests/` + cap de tamanho | (b) | Fixtures de teste têm strings com shape de segredo por natureza; o gate de segredo primário é o `gitleaks` (`secret-scan`). |
| 7 | Percorrer a árvore no `spec_verify` | `Path.rglob` (percorria `.venv`/`node_modules` — minutos) vs `os.walk` com prune de diretórios | `os.walk` + `_PRUNE_DIRS` | rglob não permite podar diretório; `os.walk` sim. |

---

## 4. Blockers / trabalho restante

- **Prova do `ci.yml`**: abrir o PR e confirmar que `changes`, os gates e o `ci-gate` resolvem — e que num PR só-de-docs os jobs caros ficam *skipped* e o `ci-gate` fica verde (AT1).
- **`integration` contra BQ real**: só roda no CI (WIF). Primeira execução prova AT2/AT3/AT5/S7 em tempo de PR.
- **Flip da branch protection**: após `ci.yml` verde uma vez, `gh api ... required_status_checks.checks = [{context: ci-gate}]` (remove `secret-scan`). Documentado; passo pós-merge (AT7).
- **Job noturno `real-source`** (bate na URL real do Tesouro): COULD G9, fora desta feature.
- **Lifecycle de objetos `citest/` no RAW bucket**: hoje herdam a regra geral (deleta ARCHIVED > 365d). Adicionar regra por prefixo `citest/` num incremento — custo ínfimo (CSVs de ~200 B).

---

## 5. Status transitions

| Arquivo | Status | Próximo |
|---|---|---|
| `DEFINE_CI_ASSURANCE_GATES.md` | `✅ Complete (Built)` | `/ship` (após PR verde + `/verify-spec`) |
| `DESIGN_CI_ASSURANCE_GATES.md` | `✅ Complete (Built)` | `/ship` |

---

## 6. Quality gate (parcial)

- [x] Todos os itens do manifesto criados/modificados (24, alguns fundidos)
- [x] Cada pacote Python verificado (ruff+format+mypy+pytest)
- [x] `spec_verify` real = PASS
- [x] Sem TODO / sem segredo
- [x] Atribuição de agente (§1) + Autonomous Decisions (§3)
- [x] DEFINE/DESIGN → `✅ Complete (Built)`
- [ ] `ci.yml` provado no CI — **pendente do PR**
- [x] BUILD_REPORT gerado

---

## 7. Revision history

| Data | Versão | Mudança | Autor |
|---|---|---|---|
| 2026-09-04 | 1.0 | Build completo em `feature/ci-assurance-gates`. `ci.yml` guarda-chuva + `ci-gate`, `spec_verify.py` + `spec-checks/SPEC-033.yaml` + `gates.yaml`, teste de integração BQ real + fixture, connector `file://`, config env overrides, workflows de deploy enxugados. 7 Autonomous Decisions. Verificação local verde; prova do CI pendente do PR. | /build (Claude Sonnet 5) |
