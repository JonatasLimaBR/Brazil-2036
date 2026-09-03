# SPEC-007 — Provenance
Every canonical metric MUST resolve:
metric → Gold object → Silver transform → Bronze object → source resource → catalog dataset → producing organization.
API: GET /v1/provenance/{metric_id}.
Response includes source URLs, reference date, transform versions and trust status.
