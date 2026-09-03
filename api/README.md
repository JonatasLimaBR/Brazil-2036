# api — metrics API (SPEC-033, SPEC-026)

Read-only FastAPI over `br2036_gold`. Two endpoints:

- `GET /v1/metrics/{metric_id}?state_ibge_code=` — value + unit + `reference_year` +
  typed `data_class` (ADR-028) + a provenance summary.
- `GET /v1/provenance/{metric_id}?state_ibge_code=` — the full SPEC-007 chain
  (gold → silver transform + version → bronze object → source resource → catalogue → org).

`trust_status` is `source_only` until a Data Trust Score exists (SPEC-006, out of scope).

## Develop

```bash
uv run --with ruff ruff check .
uv run --with mypy --with pyyaml --with fastapi --with pydantic mypy
uv run --extra dev python -m pytest -q
uv run --extra dev python scripts/export_openapi.py   # regenerate openapi/openapi.json
uv run --extra dev uvicorn api.main:app --reload      # local server (needs GCP_PROJECT + ADC)
```

## Deploy

Cloud Run service; runtime SA `api@` with `bigquery.jobUser` + `dataViewer` on
`br2036_gold` only. Built and deployed by `.github/workflows/api-web.yml`.
