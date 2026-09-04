# DESIGN — CI_ASSURANCE_GATES

## Metadados

- **Feature:** CI_ASSURANCE_GATES
- **Status:** ✅ Complete (Built)
- **Fase:** 2 (Design)
- **Entrada:** `.claude/sdd/features/DEFINE_CI_ASSURANCE_GATES.md` (Clarity 14/15)
- **Criado:** 2026-09-04
- **Idioma:** PT-BR
- **Branch:** `feature/ci-assurance-gates`
- **Confiança:** 0.82 — sem `kb/` do plugin; padrões vêm de `SPEC-031`/`SPEC-033`/ADR-036/038/040 e da doc do GitHub Actions.
- **Próximo passo:** `/build .claude/sdd/features/DESIGN_CI_ASSURANCE_GATES.md`

> Contract gate (`spec-lint`) não executável — plugin ausente.

---

## 1. Grounding

| Fonte | O que fixa |
|---|---|
| `SPEC-031` | Checks obrigatórios: format/lint/typecheck, unit, integration, contracts, security, Terraform validation, agent evals **quando afetados**, spec verification. Substituto "warning-only" não vale. |
| `SPEC-033` | O que o `spec-verify` checa (MUST list + AT); o teste de integração realiza AT1/AT3/AT4/AT5/AT6/AT7/S7 em tempo de PR. |
| `SPEC-005` | Contrato de dados (o `contract.check` já existe em `ingestion/src/ingestion/contract.py`). |
| ADR-036 | Agent evals bloqueiam merge **quando há agente** → declaração N/A explícita e legível por máquina. |
| ADR-038 | `main` protegida, PR-only (ligada 2026-09-04). |
| ADR-040 | WIF, sem chave estática. |
| RISK-MATRIX | R-006 (contrato), R-011 (secret scan), R-012 (custo — cap de bytes + TTL). |
| GitHub Actions | Um job com `if:` falso reporta **skipped**; branch protection moderna trata *skipped* como neutro — mas **não dependemos disso**: um job agregador `ci-gate` que sempre roda é o único required check. |

---

## 2. Arquitetura

### 2.1 Visão geral

```text
PR para main  /  push em main
        │
        ▼
┌──────────────────────── .github/workflows/ci.yml  (SEM filtro de path) ─────────────────────────┐
│                                                                                                 │
│  changes (dorny/paths-filter@v3)                                                                 │
│    outputs: ingestion, api, web, infra, specs, workflows                                         │
│        │                                                                                         │
│        ├─▶ lint-typecheck-unit ──(if ingestion||api||always)── ruff · mypy · pytest -m "not integration"
│        │        (ingestion + api; jobs separados ou matrizados)                                  │
│        │                                                                                         │
│        ├─▶ web-check ──(if web)── npm ci · gen:client (diff) · tsc · vite build                  │
│        │                                                                                         │
│        ├─▶ terraform ──(if infra)── fmt -check · init -backend=false · validate · plan (WIF, ro) │
│        │                                                                                         │
│        ├─▶ contracts+integration ──(if ingestion||specs, e não-fork)──                           │
│        │        bootstrap citest_<run>_{control,bronze,silver,gold} (bq mk, TTL 1h)              │
│        │        RESOURCE_URL=file://…/divida_sample.csv  BQ_DATASET_*=citest_<run>_*             │
│        │        python -m ingestion  →  assert 27→(fixture N) linhas · provenance 100% · lineage │
│        │        teardown (always): bq rm -r -f citest_<run>_*                                    │
│        │                                                                                         │
│        ├─▶ spec-verify ──(sempre)── scripts/spec_verify.py spec-checks/SPEC-033.yaml             │
│        │        + valida que .github/ci/gates.yaml cobre todo gate do SPEC-031                   │
│        │                                                                                         │
│        └─▶ secret-scan ──(sempre)── gitleaks                                                     │
│                                                                                                 │
│  ci-gate  (needs: [todos acima], if: always())                                                   │
│    FAIL se qualquer needs.*.result == 'failure' | 'cancelled'; PASS se todos success|skipped     │
│    → ESTE é o único required status check                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘

deploy (inalterado, só em push→main, path-filtered):
  data.yml → deploy-and-run   ·   api-web.yml → deploy   ·   infra.yml → apply
```

### 2.2 Componentes

| # | Componente | Papel |
|---|---|---|
| C1 | `ci.yml` | Guarda-chuva de **gates de merge**. Sem `paths`. Roda em `pull_request` (main) e `push` (main). |
| C2 | job `changes` | `dorny/paths-filter@v3` → booleans por área. Fonte única da verdade sobre "o que mudou". |
| C3 | jobs de gate | `lint-typecheck-unit` (ingestion+api), `web-check`, `terraform`, `contracts+integration`, `spec-verify`, `secret-scan`. Cada um condicional ao filtro (ou sempre). |
| C4 | job `ci-gate` | Agregador `if: always()`, `needs` todos. Falha se algum `needs.*.result` for `failure`/`cancelled`. **O único required check.** |
| C5 | `.github/ci/gates.yaml` | Manifesto SPEC-031: cada gate → job + status (`active` / `n/a` + motivo). `agent-eval: n/a`. |
| C6 | `scripts/spec_verify.py` | Verificador genérico: lê `spec-checks/SPEC-XXX.yaml`, roda checks objetivos, matriz PASS/FAIL, exit ≠ 0. |
| C7 | `spec-checks/SPEC-033.yaml` | Asserções checáveis do SPEC-033 (deliverables existem, paths do OpenAPI, regras no contrato, ausência de padrões, sem chave estática). |
| C8 | `ingestion/tests/integration/` | `test_pipeline_bigquery.py` (`@pytest.mark.integration`), `fixtures/divida_sample.csv`. |
| C9 | connector `file://` + config env | `divida_estados.py` lê `file://` além de HTTP; `config.py` aceita override por env de `resource_url` + nomes de dataset + `raw_prefix`. |
| C10 | `data.yml` / `api-web.yml` / `infra.yml` | **Modificados:** removem seus jobs de check (movidos ao `ci.yml`); mantêm só o job de **deploy/apply** (push→main). |

### 2.3 Fluxo de decisão (pass-through)

- Nenhum job "pass-through" fake. Se a área não mudou, o job de gate correspondente **não roda** (`if: needs.changes.outputs.X == 'true'` etc.) → reporta *skipped*.
- `ci-gate` roda **sempre**, `needs` todos, e só reprova em `failure`/`cancelled`. `skipped` e `success` passam. → nenhum "Expected — waiting"; um único contexto (`ci-gate`) é o required check (G7/OQ7).

### 2.4 Pontos de integração

| Dependência | Uso | Falha |
|---|---|---|
| `dorny/paths-filter@v3` | detectar mudanças | ação estável e amplamente usada; sem fallback |
| GCP via WIF (`tf-deployer`) | `terraform plan` (ro) + `contracts+integration` (cria/derruba `citest_*`) | job falha → `ci-gate` falha → merge bloqueado |
| BigQuery | datasets `citest_<run>_*` (TTL 1h, cap de bytes) | teardown em `always()`; TTL cobre teardown falho |
| Fixture local | `RESOURCE_URL=file://…` | sem rede; determinística |
| `gitleaks` | secret scan | job falha → bloqueia |

---

## 3. Decisões (ADRs inline)

### D1 — Guarda-chuva `ci.yml` + agregador `ci-gate` como único required check

| Atributo | Valor |
|---|---|
| Status | Accepted → **ADR-054** |
| Data | 2026-09-04 |

**Contexto:** os workflows são filtrados por path; um job de check filtrado não pode ser um
required status check (um PR que não toca o path deixa o check "Expected" para sempre). Confiar
no comportamento "skipped = pass" da branch protection é frágil e pouco documentado.

**Escolha:** um workflow **`ci.yml` sem filtro de path** que roda em todo PR/push para `main`,
com um job `changes` (`dorny/paths-filter`) alimentando jobs de gate condicionais, e um job
**`ci-gate`** (`if: always()`, `needs` todos) que reprova só em `failure`/`cancelled`. **`ci-gate`
é o único required status check.** Os workflows `data.yml`/`api-web.yml`/`infra.yml` perdem seus
jobs de check (movidos para `ci.yml`) e mantêm só deploy/apply em push→main.

**Racional:** um único contexto required que **sempre resolve** → zero deadlock; a lógica de
"o que precisa rodar" fica num lugar (`changes`); não depende de semântica de skipped.

**Alternativas rejeitadas:**
1. *Jobs stub sempre-verdes por área* — rejeitado: duplica jobs, e um stub que "passa" mascara ausência real de cobertura.
2. *Manter workflows separados e marcar cada check job como required* — rejeitado: o deadlock de path filter é o problema original.
3. *Depender de "skipped required = pass"* — rejeitado: comportamento não garantido entre mudanças do GitHub; `ci-gate` remove a dependência.

**Consequências:** (+) config de branch protection trivial (1 contexto); (+) full gate set visível em todo PR. (−) `ci.yml` fica grande; (−) mover os check jobs quebra o `needs` dos workflows de deploy — o deploy passa a confiar que o PR foi gated (a `main` é protegida) e mantém só um `pytest -q` rápido de pré-voo.

### D2 — `spec-verify` genérico + `spec-checks/SPEC-XXX.yaml`

| Atributo | Valor |
|---|---|
| Status | Accepted |
| Data | 2026-09-04 |

**Contexto:** `SPEC-031` exige "spec verification" como gate; o `/verify-spec` humano
(ADR-034) é independente e não pode ser automatizado por completo. Falta o **piso mecânico**.

**Escolha:** `scripts/spec_verify.py` (genérico, ~150 linhas) lê `spec-checks/SPEC-XXX.yaml` e
executa tipos de check declarativos: `files_exist`, `openapi_paths` (num `openapi.json`),
`contract_has_rules` (num contrato YAML), `grep_absent` (padrão que não pode aparecer num path),
`no_static_keys` (scan de shapes de chave de SA no repo). Matriz PASS/FAIL por item, exit ≠ 0 em
qualquer FAIL. **Não** faz juízo semântico — o `/verify-spec` humano continua obrigatório antes
do `/ship` (registrado no SPEC).

**Racional:** cobre exatamente o que é objetivamente verificável (achado do review: "arquivo
existe? endpoint responde? campo no schema?"); extensível para a fatia #2 com um novo YAML.

**Alternativas rejeitadas:**
1. *Script bespoke por SPEC* — rejeitado: N cópias divergentes.
2. *Rodar o subagente revisor no CI* — rejeitado: custo/latência/não-determinismo num gate de merge; é para o `/ship`, não para todo PR.

**Consequências:** (+) piso barato e determinístico; (−) `spec-checks/*.yaml` é mais um artefato a manter em dia (o próprio `spec-verify` falha se o YAML referencia um SPEC inexistente).

### D3 — Integração com fixture commitada, não fetch real

| Atributo | Valor |
|---|---|
| Status | Accepted |
| Data | 2026-09-04 |

**Contexto:** o gate de integração precisa ser determinístico e rápido em todo PR.

**Escolha:** `ingestion/tests/integration/fixtures/divida_sample.csv` (~6 linhas: `SP;2021`,
`SP;2022`, `RJ;2021`, `RJ;2022`, `DF;2021`, `DF;2022`), mesmo formato do real. O connector lê via
`RESOURCE_URL=file://…`. Um job **noturno** (`schedule:`) separado — **fora desta feature**, COULD
G9 futuro — pode bater na URL real do Tesouro para pegar drift de fonte.

**Racional:** zero flakiness de rede; PRs rápidos e baratos; ainda exercita a cadeia inteira
(registry → RAW → Bronze → Silver → Gold → provenance) contra BigQuery **real**.

**Alternativas rejeitadas:**
1. *Fetch real do Tesouro no gate* — rejeitado: rede no caminho crítico do merge.
2. *Emulador de BigQuery* — rejeitado (DEFINE §6): cobertura parcial de SQL (`CREATE OR REPLACE`, `LOAD DATA`, `DATE()`), não confiável.

**Consequências:** (+) determinístico; (−) drift de schema da fonte real só é pego no job noturno (futuro) ou no `data.yml` pós-merge.

### D4 — Datasets `citest_<run>_*` efêmeros + overrides por env

| Atributo | Valor |
|---|---|
| Status | Accepted |
| Data | 2026-09-04 |

**Contexto:** o teste não pode tocar `br2036_bronze/silver/gold` (C3). O `config.py` só aceita
`GCP_PROJECT`/`RAW_BUCKET` por env hoje.

**Escolha:** `config.py` passa a aceitar override por env de `resource_url`, `raw_prefix`,
`bq_dataset_control/bronze/silver/gold` (4 linhas, padrão = valor do `config.yaml`). O job
`contracts+integration`: `RUN=${{ github.run_id }}`; `for L in control bronze silver gold; do
bq mk --dataset --default_table_expiration=3600 "citest_${RUN}_${L}"; done`; exporta
`BQ_DATASET_$(upper L)=citest_${RUN}_${L}` e `RAW_PREFIX=citest/${RUN}`; roda `python -m ingestion`;
teardown `always()`: `bq rm -r -f -d` de cada `citest_${RUN}_*` (e um sweep de `citest_*` com
`labels` ou idade > 2h como rede de segurança).

**Racional:** isolamento total, teardown determinístico, TTL de 1h cobre teardown falho (R-012).

**Alternativas rejeitadas:**
1. *Um único dataset com prefixo de tabela* — rejeitado: exige reescrever as referências `${bq_dataset_*}` nos `.sql`.
2. *Projeto GCP dedicado a teste* — rejeitado: overkill para a fatia; custo/gestão.

**Consequências:** (+) zero risco de produção; (−) `config.py` ganha 4 overrides; (−) 4 `bq mk`/`bq rm` por run (~10 s, centavos).

### D5 — Integração cobre só o pipeline nesta rodada (não a API)

| Atributo | Valor |
|---|---|
| Status | Accepted |
| Data | 2026-09-04 |

**Contexto:** OQ6.

**Escolha:** o gate de integração exercita registry→…→provenance. A **API** fica coberta por
`lint-typecheck-unit` (9 testes unit) + o Playwright e2e ao vivo no `api-web.yml` pós-merge.
Subir uvicorn contra a Gold de teste + curl entra na fatia #2 se necessário.

**Racional:** o achado #7 é sobre o **pipeline** sem integração real; a API já tem e2e ao vivo.
Mantém o gate rápido.

**Consequências:** (−) uma regressão só-de-integração da API (ex.: query BQ malformada) só é
pega no e2e pós-merge — aceito; o e2e roda antes de qualquer usuário ver.

### D6 — `file://` no connector real (não um connector de teste)

| Atributo | Valor |
|---|---|
| Status | Accepted |
| Data | 2026-09-04 |

**Contexto:** o teste de integração precisa injetar a fixture sem HTTP.

**Escolha:** `DividaEstadosConnector.download()` trata `resource_url` começando com `file://`
como leitura local (o resto do fluxo — hash, `validate`, checkpoint — é idêntico). Sem
`FixtureConnector` paralelo.

**Racional:** o teste roda **o mesmo código** de produção ponta a ponta; menos superfície.
`file://` também é útil para debug local.

**Alternativas rejeitadas:** *`http.server` local servindo a fixture* — mais peças móveis;
*connector de teste* — divergência do caminho real.

**Consequências:** (+) fidelidade; (−) `download()` ganha um branch `if url.startswith("file://")`.

---

## 4. Manifesto de arquivos

| # | Arquivo | Ação | Propósito | Agente | Deps |
|---|---|---|---|---|---|
| 1 | `docs/adrs/ADR-054-ci-merge-gate-umbrella.md` | Create | Formaliza D1 (`ci.yml` + `ci-gate`) | `architect` | — |
| 2 | `.github/ci/gates.yaml` | Create | Manifesto SPEC-031 → job/status; `agent-eval: n/a` + motivo (G5, ADR-036) | `(general)` | 1 |
| 3 | `spec-checks/SPEC-033.yaml` | Create | Asserções checáveis do SPEC-033 (C7) | `(general)` | — |
| 4 | `scripts/spec_verify.py` | Create | Verificador genérico (D2); tipos `files_exist`/`openapi_paths`/`contract_has_rules`/`grep_absent`/`no_static_keys`/`gates_manifest_complete` | `python-developer` | 3 |
| 5 | `scripts/tests/test_spec_verify.py` | Create | Unit do verificador (cada tipo de check: pass + fail) | `python-developer` | 4 |
| 6 | `ingestion/src/ingestion/config.py` | Modify | env overrides: `RESOURCE_URL`, `RAW_PREFIX`, `BQ_DATASET_{CONTROL,BRONZE,SILVER,GOLD}` (D4) | `python-developer` | — |
| 7 | `ingestion/src/ingestion/connectors/divida_estados.py` | Modify | `file://` em `download()` (D6) | `ai-data-engineer-gcp` | — |
| 8 | `ingestion/tests/test_connector.py` | Modify | +teste `download()` de `file://` | `python-reviewer` | 7 |
| 9 | `ingestion/tests/integration/__init__.py` | Create | pacote de integração | `(general)` | — |
| 10 | `ingestion/tests/integration/fixtures/divida_sample.csv` | Create | ~6 linhas (SP/RJ/DF × 2021/2022), formato `UF;ANO;VALOR` | `(general)` | — |
| 11 | `ingestion/tests/integration/test_pipeline_bigquery.py` | Create | `@pytest.mark.integration` — `python -m ingestion` contra BQ real + `citest_*`; afirma linhas = distinct UF da fixture, provenance 100%, lineage fecha (S7); skip sem `GCP_PROJECT` | `data-quality-analyst` | 6,7,10 |
| 12 | `ingestion/pyproject.toml` | Modify | `markers = ["integration: needs real GCP"]`; `pytest -m "not integration"` default no unit | `python-developer` | — |
| 13 | `ingestion/README.md` | Modify | rodar integração local (`RESOURCE_URL=file://…`, `bq mk`…) | `code-documenter` | 11 |
| 14 | `.github/workflows/ci.yml` | Create | Guarda-chuva: `changes` + gates condicionais + `ci-gate` (D1) | `ci-cd-specialist` | 2,4,11 |
| 15 | `.github/workflows/data.yml` | Modify | remove `data-checks`; `deploy-and-run` mantém `pytest -q` de pré-voo; trigger inalterado | `ci-cd-specialist` | 14 |
| 16 | `.github/workflows/api-web.yml` | Modify | remove `api-web-checks`; `deploy` mantém pré-voo mínimo | `ci-cd-specialist` | 14 |
| 17 | `.github/workflows/infra.yml` | Modify | move `fmt/validate/plan` para `ci.yml`; mantém só `apply` (push→main) | `ci-cd-specialist` | 14 |
| 18 | `.github/workflows/security.yml` | Modify | secret-scan passa a viver no `ci.yml`; `security.yml` fica só como fallback de `push` ou é removido | `security-reviewer` | 14 |
| 19 | `.github/CODEOWNERS` | Modify | `+/spec-checks/ +/scripts/`; `+.github/ci/` | `(general)` | — |
| 20 | `docs/specs/SPEC-031-CI-GATES.md` | Modify | referencia `ci.yml`+`ci/gates.yaml` como realização; mecanismo `agent-eval` N/A; `spec-verify` = piso, `/verify-spec` humano continua | `architect` | 1,2 |
| 21 | `docs/adrs/ADR-036-agent-evals-block-merge.md` | Modify | back-ref: N/A declarado em `ci/gates.yaml` enquanto não houver agente | `architect` | 2 |
| 22 | `INDEX.md` | Modify | +ADR-054, +`.github/ci/gates.yaml`, +`spec-checks/` | `(general)` | 1,2,3 |
| — | branch protection | (op) | `required_status_checks` → só `ci-gate` (após `ci.yml` verde uma vez); documentado no BUILD_REPORT | `ci-cd-specialist` | 14 |

### Racional de agentes
- `.yml` de workflow + `gh api` → `ci-cd-specialist`.
- Python (verificador, config, integração) → `python-developer` / `ai-data-engineer-gcp` (connector GCP) / `data-quality-analyst` (asserções de qualidade).
- ADR/SPEC → `architect`; README → `code-documenter`; YAML declarativo → `(general)`.
- Revisão transversal: `code-reviewer` + `security-reviewer` (o `security.yml` mexe em gate de segurança).

### Independência
- `ci.yml` é o único novo "deployable" (workflow). Sem código compartilhado com os de deploy; a única dependência é conceitual (deploy confia que o PR foi gated).
- Sem ciclo: `changes` → gates → `ci-gate`. Linear.

---

## 5. Padrões de código

### 5.1 `ci-gate` agregador

```yaml
  ci-gate:
    name: ci-gate
    needs: [changes, lint-typecheck-unit, web-check, terraform, integration, spec-verify, secret-scan]
    if: always()
    runs-on: ubuntu-latest
    steps:
      - name: fail if any required gate failed
        run: |
          bad=0
          for r in \
            "${{ needs.lint-typecheck-unit.result }}" \
            "${{ needs.web-check.result }}" \
            "${{ needs.terraform.result }}" \
            "${{ needs.integration.result }}" \
            "${{ needs.spec-verify.result }}" \
            "${{ needs.secret-scan.result }}"; do
            case "$r" in
              success|skipped) ;;
              *) echo "gate result: $r"; bad=1 ;;
            esac
          done
          exit $bad
```

### 5.2 `changes` job

```yaml
  changes:
    runs-on: ubuntu-latest
    outputs:
      ingestion: ${{ steps.f.outputs.ingestion }}
      api:       ${{ steps.f.outputs.api }}
      web:       ${{ steps.f.outputs.web }}
      infra:     ${{ steps.f.outputs.infra }}
      specs:     ${{ steps.f.outputs.specs }}
    steps:
      - uses: actions/checkout@v4
      - id: f
        uses: dorny/paths-filter@v3
        with:
          filters: |
            ingestion: ['ingestion/**']
            api:       ['api/**']
            web:       ['web/**', 'api/openapi/openapi.json']
            infra:     ['infra/terraform/**']
            specs:     ['docs/specs/**', 'spec-checks/**', '.github/ci/gates.yaml']
```

### 5.3 `integration` job (núcleo)

```yaml
  integration:
    needs: changes
    if: >-
      (needs.changes.outputs.ingestion == 'true' || needs.changes.outputs.specs == 'true')
      && (github.event_name != 'pull_request'
          || github.event.pull_request.head.repo.full_name == github.repository)
    runs-on: ubuntu-latest
    permissions: { contents: read, id-token: write }
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ vars.GCP_WIF_PROVIDER }}
          service_account: ${{ vars.GCP_DEPLOYER_SA }}
      - uses: google-github-actions/setup-gcloud@v2
      - name: run integration
        working-directory: ingestion
        run: |
          RUN="${{ github.run_id }}"
          for L in control bronze silver gold; do
            bq --project_id="${{ vars.GCP_PROJECT }}" mk --dataset \
              --default_table_expiration=3600 "citest_${RUN}_${L}"
            U=$(echo "$L" | tr a-z A-Z)
            echo "BQ_DATASET_${U}=citest_${RUN}_${L}" >> "$GITHUB_ENV"
          done
          echo "RAW_PREFIX=citest/${RUN}" >> "$GITHUB_ENV"
          echo "RESOURCE_URL=file://$(pwd)/tests/integration/fixtures/divida_sample.csv" >> "$GITHUB_ENV"
      - name: pipeline + asserts
        working-directory: ingestion
        env:
          GCP_PROJECT: ${{ vars.GCP_PROJECT }}
          RAW_BUCKET: ${{ vars.GCP_PROJECT }}-raw
        run: uv run --extra dev python -m pytest -q -m integration
      - name: teardown
        if: always()
        run: |
          RUN="${{ github.run_id }}"
          for L in control bronze silver gold; do
            bq --project_id="${{ vars.GCP_PROJECT }}" rm -r -f -d "citest_${RUN}_${L}" || true
          done
      - name: fork PR note
        if: github.event.pull_request.head.repo.full_name != github.repository && github.event_name == 'pull_request'
        run: echo "integration skipped: no GCP credentials on fork PR"
```

### 5.4 `spec_verify.py` (forma)

```python
# scripts/spec_verify.py
from __future__ import annotations
import json, re, sys
from pathlib import Path
import yaml

CHECKS = {}

def check(name):
    def deco(fn): CHECKS[name] = fn; return fn
    return deco

@check("files_exist")
def _files_exist(spec, items, root):
    return [(f"file {p}", (root / p).exists(), "") for p in items]

@check("openapi_paths")
def _openapi_paths(spec, cfg, root):
    schema = json.loads((root / cfg["file"]).read_text())
    have = set(schema.get("paths", {}))
    return [(f"openapi path {p}", p in have, "") for p in cfg["paths"]]

@check("contract_has_rules")
def _contract_has_rules(spec, cfg, root):
    text = (root / cfg["file"]).read_text()
    return [(f"contract rule /{rx}/", re.search(rx, text) is not None, "")
            for rx in cfg["patterns"]]

@check("grep_absent")
def _grep_absent(spec, cfg, root):
    hits = [str(p) for p in (root / cfg["path"]).rglob("*")
            if p.is_file() and cfg["pattern"] in p.read_text(errors="ignore")]
    return [(f"absent {cfg['pattern']!r} in {cfg['path']}", not hits, "; ".join(hits))]

@check("gates_manifest_complete")
def _gates(spec, cfg, root):
    manifest = yaml.safe_load((root / cfg["file"]).read_text())["gates"]
    required = set(cfg["required_gates"])
    covered = {g for g, v in manifest.items()
               if v.get("status") in ("active", "n/a")}
    missing = required - covered
    return [(f"SPEC-031 gate '{g}' declared", g in covered, "") for g in required] + \
           [("no undeclared gate", not missing, ", ".join(sorted(missing)))]

def main() -> int:
    root = Path(__file__).resolve().parents[1]
    spec_yaml = yaml.safe_load(Path(sys.argv[1]).read_text())
    rows = []
    for kind, arg in spec_yaml["checks"].items():
        rows += CHECKS[kind](spec_yaml["spec"], arg, root)
    ok = True
    for label, passed, detail in rows:
        print(f"{'PASS' if passed else 'FAIL'} | {label}" + (f" — {detail}" if detail and not passed else ""))
        ok &= passed
    print(f"\n{spec_yaml['spec']}: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
```

### 5.5 `spec-checks/SPEC-033.yaml`

```yaml
spec: SPEC-033
checks:
  files_exist:
    - api/scripts/export_openapi.py
    - api/openapi/openapi.json
    - ingestion/contracts/divida_consolidada_estados.yaml
    - ingestion/reference/uf_ibge.csv
    - infra/terraform/versions.tf
    - scripts/bootstrap.sh
  openapi_paths:
    file: api/openapi/openapi.json
    paths: ["/v1/metrics/{metric_id}", "/v1/provenance/{metric_id}"]
  contract_has_rules:
    file: ingestion/contracts/divida_consolidada_estados.yaml
    patterns: ['count\(distinct state_ibge_code\) = 27', 'min:\s*0', 'evolution_policy']
  grep_absent:
    path: web/src
    pattern: "divida_consolidada_liquida"
  gates_manifest_complete:
    file: .github/ci/gates.yaml
    required_gates: [format, lint, typecheck, unit, integration, contracts, security, terraform, spec-verify, agent-eval]
```

### 5.6 `config.py` — override por env (trecho)

```python
def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)

# ... dentro de load_config():
    resource_url=_env("RESOURCE_URL", raw["resource_url"]),
    raw_prefix=_env("RAW_PREFIX", raw["raw_prefix"]),
    bq_dataset_control=_env("BQ_DATASET_CONTROL", raw["bq_dataset_control"]),
    bq_dataset_bronze=_env("BQ_DATASET_BRONZE", raw["bq_dataset_bronze"]),
    bq_dataset_silver=_env("BQ_DATASET_SILVER", raw["bq_dataset_silver"]),
    bq_dataset_gold=_env("BQ_DATASET_GOLD", raw["bq_dataset_gold"]),
```

### 5.7 connector `file://` (trecho)

```python
def download(self, ref: ResourceRef, dest: str) -> DownloadResult:
    if ref.resource_url.startswith("file://"):
        src = ref.resource_url[len("file://"):]
        data = Path(src).read_bytes()
        Path(dest).write_bytes(data)
        return DownloadResult(dest, hashlib.sha256(data).hexdigest(), 200, len(data), 1, [])
    # ... HTTP path inalterado
```

---

## 6. Estratégia de testes

Esta feature **é** infraestrutura de teste. "Testar" = provar que cada gate pega o que deve.

| AT | Como verificar |
|---|---|
| AT1 pass-through | PR descartável mudando só `README.md` → todos os jobs de gate *skipped*, `ci-gate` verde < 90 s. |
| AT2 execução real | PR mudando `ingestion/src/**` → `lint-typecheck-unit` + `integration` rodam de verdade; `integration` cria/derruba `citest_*`. |
| AT3 contrato | PR que adiciona `patterns: ['coluna_inexistente']`… na verdade: PR que quebra a Silver (remove o JOIN com `uf_ibge`) → `integration` vermelho. |
| AT4 deliverable | PR que `git rm api/openapi/openapi.json` → `spec-verify` FAIL no `files_exist`. |
| AT5 sem órfão | rodar `integration` 3×; `bq ls` sem `citest_*` (teardown `always()` + TTL). |
| AT6 WIF/fork | inspeção do `ci.yml` (`auth@v2` + provider, sem key); simular fork PR → job `integration` skipped + nota. |
| AT7 branch protection | `gh api …/branches/main/protection` → `required_status_checks.checks` == `[ci-gate]`. |
| AT8 falha bloqueia | PR com `lint-typecheck-unit` vermelho → `gh pr view` `mergeable = CONFLICTING`/`mergeStateStatus = BLOCKED`. |
| AT9 agent-eval N/A | `spec_verify` `gates_manifest_complete` exige `agent-eval` presente em `gates.yaml` com `status: n/a`. |
| unit | `scripts/tests/test_spec_verify.py` — cada tipo de check com um caso PASS e um FAIL; `pytest` roda em `lint-typecheck-unit` (novo path `scripts/`). |
| integração (a própria) | `test_pipeline_bigquery.py` roda no gate `integration` e localmente com `-m integration` + `GCP_PROJECT`. |

**Rollout:** primeiro commit cria `ci.yml` mas **não** muda branch protection; depois de `ci.yml`
passar verde num PR real, um passo `gh api` troca o required check para `ci-gate` (documentado no
BUILD_REPORT). Remoção dos check jobs de `data.yml`/`api-web.yml` no mesmo PR.

---

## 7. Pipeline Architecture (contexto DE — o gate de integração)

### 7.1 DAG do teste

```text
bq mk citest_<run>_{control,bronze,silver,gold}  (TTL 1h)
        │
        ▼
RESOURCE_URL=file://…/divida_sample.csv
        │
python -m ingestion  (mesmo entrypoint de produção)
  registry.upsert (citest_<run>_control)  → uf_ibge, dataset_registry
  connector.download (file://) → raw.write (gs://…-raw/citest/<run>/<sha>.csv)
  bronze.load (citest_<run>_bronze)
  contract.check(bronze)
  silver.sql / gold.sql (citest_<run>_silver / _gold)
  provenance.write_from_gold (citest_<run>_gold)
  contract.check(gold)  → linhas = distinct UF da fixture; provenance 100%
        │
pytest asserts (lineage query cruza registry→raw→bronze→silver→gold→provenance)
        │
teardown always(): bq rm -r -f -d citest_<run>_*
```

### 7.2 Partição / incremental / evolução
- Mesmas tabelas do pipeline real (partição por `reference_date`, `CREATE OR REPLACE`).
- A fixture cobre 2 anos → o teste também valida `MAX(reference_year)` e que a Gold guarda ambos.
- Sem mudança de schema evolution.

### 7.3 Data quality gates (no teste)
| Gate | Regra (fixture) | Falha ⇒ |
|---|---|---|
| Schema origem | `UF;ANO;VALOR` | teste falha |
| Territorial | toda UF da fixture em `uf_ibge` | teste falha |
| Completude | `COUNT(distinct state_ibge_code)` == nº de UF distintas na fixture (3) para `MAX(reference_year)` | teste falha |
| Integridade | NOT NULL PK, `value >= 0` | teste falha |
| Provenance | 100% cobertura | teste falha |
| Lineage | query de S7 fecha para ≥ 1 UF | teste falha |

> A contagem "27" do contrato de produção é imposta pelo `verify_chain.py` no `data.yml`
> pós-merge; no gate de integração o assert usa a contagem da fixture (senão nunca passaria).
> `check_gold` recebe `expected_entity_count` do contrato — o teste de integração usa um contrato
> de fixture (`tests/integration/fixtures/contract_fixture.yaml`, `= 3`) OU parametriza o assert.
> **Decisão:** contrato de fixture próprio (mantém o de produção intocado). Adicionar ao manifesto.

---

## 8. Quality gate (Fase 2)

- [x] Padrões carregados de `SPEC-031`/`SPEC-033`/ADR-036/038/040 + doc GitHub Actions (sem `kb/`); confiança 0.82.
- [x] Diagrama ASCII (§2.1) + DAG do teste (§7.1).
- [x] ≥ 1 decisão com racional completo — D1–D6 (seis ADRs inline; D1 → ADR-054).
- [x] Manifesto completo — 22 itens + passo de branch protection.
- [x] Agente por arquivo (§4).
- [x] Snippets prontos (§5.1–5.7).
- [x] Estratégia de testes cobre AT1–AT9 + unit do verificador + a própria integração (§6).
- [x] Sem dependência de código entre unidades (só a conceitual deploy↔gate).
- [x] Sem ciclo (`changes` → gates → `ci-gate`).
- [x] Status do DEFINE → `✅ Complete (Designed)`.

**Ajuste ao §7.3 detectado no próprio design:** o `check_gold` do contrato de produção exige 27
entes; o teste de integração precisa de um **contrato de fixture** (`= 3`). Adicionado ao
manifesto como item implícito de `test_pipeline_bigquery.py` (fixture `contract_fixture.yaml`).

---

## 9. Handoff

Pronto para **`/build .claude/sdd/features/DESIGN_CI_ASSURANCE_GATES.md`** na branch
`feature/ci-assurance-gates`.

Ordem sugerida: docs (1) → `gates.yaml`+`spec-checks` (2,3) → `spec_verify.py`+testes (4,5) →
config/connector + testes (6–8) → fixtures + teste de integração (9–11) → `pyproject`/README
(12,13) → `ci.yml` (14) → modificar workflows de deploy (15–18) → CODEOWNERS/SPEC-031/ADR-036/INDEX
(19–22) → (após `ci.yml` verde num PR) trocar o required check para `ci-gate`.

---

## 10. Revision history

| Data | Versão | Mudança | Autor |
|---|---|---|---|
| 2026-09-04 | 1.0 | Criação a partir de `DEFINE_CI_ASSURANCE_GATES.md`. D1–D6 (D1→ADR-054); manifesto 22 itens; OQ1–OQ7 resolvidas. Status → Ready for Build. | /design (Claude Sonnet 5) |
| 2026-09-04 | 1.1 | Build concluída (24 itens; 7 Autonomous Decisions no BUILD_REPORT). Status → ✅ Complete (Built). | /build (Claude Sonnet 5) |
