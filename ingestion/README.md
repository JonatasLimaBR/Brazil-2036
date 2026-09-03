# ingestion — MVP walking skeleton (SPEC-033)

Batch job that proves the provenance chain for one open dataset:
`dados.gov.br` catalogue → Tesouro Transparente CKAN CSV → GCS RAW (immutable) →
BigQuery Bronze → Silver → Gold → `metric_provenance`.

Dataset: **Dívida Consolidada dos Estados e do DF** (`UF;ANO;VALOR`, `;`, pt-BR
numbers, UTF-8, annual). Canonical metric: `divida_consolidada` (gross, PAF — see
`docs/adrs/ADR-052` and DESIGN D12), not DCL.

## Layout

| Path | Role |
|---|---|
| `src/ingestion/connectors/base.py` | SPEC-003 connector Protocol + bounded retry |
| `src/ingestion/connectors/divida_estados.py` | Concrete connector for the CKAN CSV |
| `src/ingestion/parsing.py` | pt-BR number and year parsing, fiscal year-end date |
| `src/ingestion/contract.py` | Data contract v1 loader + Bronze/Gold checks (SPEC-005) |
| `src/ingestion/config.yaml` | Resource URL, table names, project (filled per environment) |
| `contracts/divida_consolidada_estados.yaml` | Data contract v1 (immutable after release) |
| `reference/uf_ibge.csv` | `UF` (2-letter) → IBGE code de-para (ADR-011) |
| `sql/silver/debt_state.sql`, `sql/gold/gold_debt_state_current.sql` | Dataform-shaped models (ADR-052) |

## Not yet implemented (needs a GCP dev project + WIF — BUILD_REPORT P2/P4)

`raw.py`, `bronze.py`, `registry.py`, `provenance.py`, `pipeline.py`,
`infra/terraform/**`, `.github/workflows/data.yml`.

## Develop

```bash
# lint + type-check + tests (no GCP needed for the current slice)
uv run --with ruff ruff check .
uv run --with mypy --with pyyaml --with requests mypy
uv run --with pytest --with pyyaml --with requests python -m pytest -q
```

## Run the job (once the GCP-bound modules land)

```bash
# manual trigger (OQ7 — Cloud Scheduler is a later COULD)
gcloud run jobs execute br2036-ingestion --region <region> --project <dev-project>
```
