# SPEC-002 — Open Data Discovery
Scan dados.gov.br metadata, store dataset/resource metadata, detect new/changed resources, classify domain/module and produce recommendations.
Discovery MUST NOT auto-promote a new dataset to production ingestion.
Every discovery run stores run_id, started_at, completed_at, counts and errors.
