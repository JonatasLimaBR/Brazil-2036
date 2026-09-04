# SPEC-031 — Blocking CI
Required checks: format/lint/typecheck where applicable, unit, integration, contracts, security, Terraform validation, agent evals when affected, spec verification.
A required failure blocks merge. Warning-only replacements are not acceptable for critical gates.

## Realization (ADR-054)
All merge gates run in `.github/workflows/ci.yml`, on every PR to `main` and every push to `main`, with no path filter. A `changes` job (`dorny/paths-filter`) drives conditional gate jobs; a `ci-gate` aggregator job (`if: always()`) is the **single required status check** — it fails only when a gate job result is `failure`/`cancelled` (`success`/`skipped` pass). `data.yml`/`api-web.yml`/`infra.yml` keep only their deploy/apply jobs, post-merge.

`.github/ci/gates.yaml` maps each gate above to its job (`status: active`) or declares it not applicable (`status: n/a` + `reason`). `scripts/spec_verify.py` asserts the manifest covers every gate.

- **spec verification** = `scripts/spec_verify.py spec-checks/SPEC-XXX.yaml` — a mechanical floor (deliverables exist, endpoints present in the OpenAPI, contract thresholds present, forbidden patterns absent, no static-key shapes, gates manifest complete). It does **not** replace the independent human `/verify-spec` (ADR-034), which stays mandatory before `/ship`.
- **integration + contracts** = `pytest -m integration` in `ingestion/` runs the real pipeline against ephemeral `citest_<run>_*` BigQuery datasets (fixture input, WIF auth, teardown on `always()`).
- **agent-eval** = `n/a` in `gates.yaml` until an agent exists (ADR-036).
