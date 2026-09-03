# SPEC-022 — Persisted Approval Workflow
States: REQUESTED, PAUSED, APPROVED, REJECTED, EXPIRED, EXECUTED, FAILED.
High-impact action stores parameters hash before approval.
Execution endpoint refuses any action without matching APPROVED record.
Security-critical actions require approver != requester.
