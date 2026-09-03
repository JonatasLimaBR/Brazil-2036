# SPEC-001 — GCP Foundation
## MUST
- Separate dev/stg/prod projects for data, AI and app concerns where practical.
- Terraform is the source of infrastructure changes.
- CI authenticates through Workload Identity Federation; no long-lived JSON key.
- Secrets live in Secret Manager.
- Privileged identities use least privilege and MFA where user-facing.
## Deliverables
Terraform modules for projects/services/IAM/budgets/log sinks.
## Acceptance
`terraform validate` passes; plan contains no public exposure not declared in ADR; no static key in repo.
