# SPEC-033 — MVP Walking Skeleton

Thin vertical slice proving the provenance chain end to end on one real open dataset:
open-data resource → GCS RAW (immutable) → BigQuery Bronze → Silver → Gold → one
canonical metric with a full provenance object → public Landing card.
Dataset: "Dívida Consolidada dos Estados e do DF" — CSV `UF;ANO;VALOR` hosted on the
Tesouro Transparente CKAN (org COREM/STN, ODbL, annual, PAF context), catalogued on
`dados.gov.br`. The canonical metric is `divida_consolidada` — **gross** consolidated
debt (PAF), **annual** per UF — not DCL (see DESIGN D12). Runs in one GCP dev project
only. Delivered in two PRs (ADR-051, ADR-052 apply).

Traceability: requirements R1–R14 and acceptance tests AT1–AT11 are defined in
`.claude/sdd/features/DEFINE_MVP_WALKING_SKELETON.md`; architecture in
`.claude/sdd/features/DESIGN_MVP_WALKING_SKELETON.md`; the resource inspection in
`.claude/sdd/features/DISCOVERY_MVP_WALKING_SKELETON.md`.

## MUST — PR1 (data spine)
- Register exactly one active row in `br2036_control.dataset_registry` for the resource
  (`resource_format='csv'`, `license='ODbL'`, `organization='COREM/STN'`, `update_frequency='annual'`,
  `br2036_domain='fiscal'`, `br2036_module='M02'`; `resource_url` = the CKAN CSV download URL;
  `source_url` = the dados.gov.br catalogue entry — to be confirmed, OQ9); discovery MUST NOT
  auto-promote (SPEC-002).
- Connector implements the SPEC-003 interface (`discover/metadata/download/validate/checkpoint`)
  with bounded, recorded retries; checkpoint skips reload when the resource hash is unchanged.
  CSV parse config: delimiter `;`, decimal `,`, thousands `.`, UTF-8; source columns `UF;ANO;VALOR`.
- RAW is immutable: object name carries the content SHA-256, a `.manifest.json` accompanies it,
  existing objects are never overwritten (ADR-005, SPEC-004).
- Layers: `br2036_bronze.debt_state_raw` (source-shaped: `UF`, `ANO`, `VALOR` as STRING +
  `_source_uri`, `_ingested_at`, `_row_hash`); `br2036_silver.debt_state` (typed; `UF` (2-letter)
  → `state_ibge_code` via `br2036_control.uf_ibge`; `ANO` → `reference_year INT64` and
  `reference_date = DATE(ANO,12,31)`; `VALOR` (pt-BR number) → `value NUMERIC`, `unit='BRL'`);
  `br2036_gold.gold_debt_state_current` (key `(state_ibge_code, reference_year)`,
  `metric_id='divida_consolidada'`, `data_class='observed'`, carries `reference_date`).
- An unmapped `UF` fails the run; no silent drop (ADR-011).
- Data contract v1 (`ingestion/contracts/divida_consolidada_estados.yaml`, SPEC-005) is enforced
  at two points: Bronze→Silver (breaking drift ⇒ quarantine, nothing promoted, non-zero exit,
  alert — SPEC-004, ADR-052) and Gold (28 rows for `MAX(reference_year)`, NOT NULL on
  `state_ibge_code`/`reference_year`/`reference_date`/`value`, `value >= 0`, provenance coverage).
- `br2036_gold.metric_provenance` has one row per metric row resolving
  `metric → Gold → Silver transform → Bronze → source resource → catalog dataset → org`
  (SPEC-007), with `scenario='observed'`, `model='none'`, `confidence=1.0`.
- SQL models are Dataform-shaped `.sql` files executed via the BigQuery client (ADR-052).
- Infrastructure is created only by Terraform in one dev project (GCS RAW bucket with versioning
  + lifecycle, BigQuery datasets `control/bronze/silver/gold`, Artifact Registry, Cloud Run Job,
  least-privilege service accounts, WIF pool, budget). No org/folders, no stg/prod (SPEC-001
  subset, ADR-039, ADR-040).
- CI authenticates via Workload Identity Federation; no static key in the repo (SPEC-031, R-011).

## MUST — PR2 (presentation)
- FastAPI/Pydantic service exposes `GET /v1/metrics/{metric_id}` (with optional
  `state_ibge_code`) returning `value`, `unit`, `reference_year`, `reference_date`, typed
  `data_class` (`observed|estimated|simulated`, ADR-028) and a provenance summary; and
  `GET /v1/provenance/{metric_id}` returning the full SPEC-007 chain.
- `openapi.json` is generated in CI; the TypeScript client is generated from it; the frontend
  does not hand-copy DTOs (ADR-024, SPEC-026).
- Public Landing renders one card: value, `reference_year` (latest published =
  `MAX(reference_year)`), a "fonte" link to the real `source_url`, and a visual `data_class`
  marker. The value is fetched from the API at runtime — no hardcoded number in the bundle
  (ADR-012).
- API and web deploy as separate Cloud Run services; web is publicly invokable, API read-only on
  `br2036_gold` (ADR-044).

## Deliverables
- `infra/terraform/**`, `ingestion/**` (connector, RAW/Bronze/Silver/Gold, contract, provenance,
  pipeline, `reference/uf_ibge.csv`, tests), `api/**`, `web/**`.
- `.github/workflows/data.yml`, `.github/workflows/api-web.yml`, `.github/workflows/security.yml`;
  `CODEOWNERS` entries for `infra/**`, `ingestion/contracts/**`, `api/**`, `web/**`, `docs/adrs/**`,
  `docs/specs/**`.
- ADR-051, ADR-052.

## Acceptance
- All AT1–AT11 pass. `terraform validate` passes and `plan` declares no public exposure outside
  an ADR; no static key in the repo (R-011). Regenerated `openapi.json` and TS client match what
  is committed. Playwright e2e confirms the card value comes from the API and the bundle contains
  no hardcoded number. Required CI gates are green; `agent-eval` is N/A (no agent affected,
  SPEC-031). `/verify-spec` returns PASS per requirement in a fresh reviewer session.

## Future work (not in this SPEC)
- Adopt Dataform for the Silver/Gold `.sql` files (closes ADR-052, restores full ADR-007).
- Reconcile `gold_debt_state_current` with the `CONTEXTO §10` Gold products
  (`gold_debt_trajectory`, `gold_state_profile`).
- DCL / DCL-RCL ratio (needs RCL from another source), full stale-source blocking (R-008),
  Data Trust Score (SPEC-006), semantic layer (SPEC-008), historical series on the card,
  INSS as slice #2.
- Confirm the dados.gov.br catalogue URL for `dataset_registry.source_url` (OQ9).
