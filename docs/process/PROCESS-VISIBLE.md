# Processo Visível no GitHub

## Branch
`main` protegida. Sem direct push.
`feature/*`, `fix/*`, `docs/*`, `chore/*`.

## Commits
Conventional Commits: feat, fix, docs, test, refactor, chore, ci, perf.

## Pull Request
Todo PR referencia:
- problema;
- PRD;
- SPEC;
- ADRs;
- riscos;
- testes;
- evidências.

## Required checks
format/lint/typecheck
unit
integration
contracts
security
terraform
agent-evals (quando afetado)
spec-verifier

Falha obrigatória bloqueia merge.

## Review
Author Agent implementa.
Fresh Reviewer Agent valida sem write.
Human reviewer aprova áreas críticas.
