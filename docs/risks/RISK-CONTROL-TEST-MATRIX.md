# Risk → Control → Test
| Risco | Controle arquitetural | Teste/gate |
|---|---|---|
| R-001 | metric tool + Semantic Layer | eval_grounded_metric |
| R-002 | capability absence | test_no_write_tool |
| R-003 | typed OBSERVED/ESTIMATED/SIMULATED | test_output_classification |
| R-004 | persisted approval checkpoint | test_publish_requires_approval |
| R-005 | redaction before trace | test_trace_redaction |
| R-006 | Data Contract + quarantine | contract_test_breaking_drift |
| R-007 | champion/challenger gate | model_quality_gate |
| R-008 | freshness + source health | test_stale_source_block |
| R-009 | RBAC+ABAC default deny | authorization_matrix_test |
| R-010 | reviewer read-only | reviewer_permission_test |
| R-011 | secret scan + Secret Manager | secret_scan |
| R-012 | `maximum_bytes_billed` por query — **implementado** (`SPEC-034`/`ADR-057`); budgets + billing export — **não implementado** (`EPIC-042`) | `test_bigquery_io.py::test_run_sql_applies_default_cap_by_default`; `test_bigquery_repo.py::test_build_bigquery_run_query_applies_cost_cap` |
| R-013 | methodology + sensitivity | index_transparency_test |
| R-014 | identification diagnostics | causal_not_identified_test |
| R-015 | no punitive tools | fraud_agent_capability_test |
