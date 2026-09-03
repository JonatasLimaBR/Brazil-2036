# SPEC-031 — Blocking CI
Required checks: format/lint/typecheck where applicable, unit, integration, contracts, security, Terraform validation, agent evals when affected, spec verification.
A required failure blocks merge. Warning-only replacements are not acceptable for critical gates.
