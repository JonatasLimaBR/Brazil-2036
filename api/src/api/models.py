from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

_TRUST_DESC = "Provenance trust status; 'source_only' until a Data Trust Score exists (SPEC-006)"


class DataClass(StrEnum):
    observed = "observed"
    estimated = "estimated"
    simulated = "simulated"


class ProvenanceSummary(BaseModel):
    source: str = Field(description="URL of the source resource")
    reference_date: str
    trust_status: str = Field(description=_TRUST_DESC)


class MetricResponse(BaseModel):
    metric_id: str
    state_ibge_code: str
    value: float
    unit: str
    reference_year: int
    reference_date: str
    data_class: DataClass
    provenance: ProvenanceSummary


class NationalMetricResponse(BaseModel):
    metric_id: str
    value: float
    unit: str
    reference_date: str
    data_class: DataClass
    provenance: ProvenanceSummary


class ProvenanceResponse(BaseModel):
    metric_id: str
    state_ibge_code: str
    reference_year: int
    reference_date: str
    gold_object: str
    silver_transform: str
    silver_transform_version: str
    bronze_object: str
    source_resource_url: str
    catalog_dataset_id: str
    producing_organization: str
    trust_status: str


# --- DebtLab simulator (SPEC-010/SPEC-016/ADR-059) -------------------------
#
# n_iterations/horizon_years are bounded (not just typed) as a defensive
# measure against the API's first-ever public write endpoint having no
# RBAC/rate-limiting yet (DESIGN §0.6) -- cheap to enforce, reduces the worst
# case cost/BigQuery-DML-quota impact of an abusive request, without building
# rate-limiting infrastructure that belongs to a future RBAC/ABAC slice.
_MIN_ITERATIONS, _MAX_ITERATIONS = 100, 20_000
_MIN_HORIZON, _MAX_HORIZON = 1, 30


class AssumptionDistributionInput(BaseModel):
    mean: float = Field(description="Fraction, e.g. 0.10 for 10%, not 10")
    std: float = Field(ge=0, description="Standard deviation, same unit as mean")


class DebtLabScenarioRequest(BaseModel):
    horizon_years: int = Field(default=10, ge=_MIN_HORIZON, le=_MAX_HORIZON)
    juros_nominal: AssumptionDistributionInput
    crescimento_nominal_pib: AssumptionDistributionInput
    primario_pct_pib: AssumptionDistributionInput
    n_iterations: int = Field(default=5000, ge=_MIN_ITERATIONS, le=_MAX_ITERATIONS)
    seed: int = Field(default=42)


class YearlyDeterministic(BaseModel):
    year_offset: int
    divida_pib_pct: float


class YearlyPercentiles(BaseModel):
    year_offset: int
    p10: float
    p25: float
    p50: float
    p75: float
    p90: float


class DebtLabScenarioBase(BaseModel):
    reference_date: str = Field(description="Most recent real divida_bruta_pib period used")
    divida_pib_pct: float = Field(description="Real observed value at reference_date")
    source: str = Field(description="URL of the source series (BCB SGS 13762)")


class DebtLabScenarioResponse(BaseModel):
    scenario_id: str
    created_at: str
    horizon_years: int
    base: DebtLabScenarioBase
    assumptions: DebtLabScenarioRequest
    engine_version: str
    seed: int
    n_iterations: int
    deterministic_trajectory: list[YearlyDeterministic]
    percentiles: list[YearlyPercentiles]
    data_class: DataClass = DataClass.simulated


# --- Suggested assumptions (MACRO_TWIN_EXPANSION, ADR-060) -----------------
#
# Read-only: derives a mean/std suggestion for DebtLab premises from real
# ingested series (selic_mensal, pib_mensal) over a trailing window. Never
# written by the caller, never applied automatically to POST
# /v1/simulations/debtlab (DESIGN D3) -- the caller decides whether to copy
# these values into their own scenario request.


class SuggestedAssumption(BaseModel):
    mean: float = Field(description="Fraction, e.g. 0.10 for 10%, not 10")
    std: float = Field(ge=0, description="Standard deviation, same unit as mean")
    window_months: int = Field(description="Number of real trailing months used")
    source_metric_id: str = Field(description="Gold metric_id the suggestion was derived from")
    period_start: str
    period_end: str
    methodology: str = Field(
        description="Plain-text note on how mean/std were derived from the real series"
    )


class SuggestedAssumptionsResponse(BaseModel):
    juros_nominal: SuggestedAssumption
    crescimento_nominal_pib: SuggestedAssumption
    # 'estimated' (ADR-028), not 'observed': mean/std are a real deterministic
    # derivation (annualization / YoY averaging) over observed data, not
    # themselves a directly observed value.
    data_class: DataClass = DataClass.estimated


# --- RAG provenance Q&A (RAG_PROVENANCE_QA, ADR-061, SPEC-018) -------------
#
# A Q&A answer is neither observed, estimated, nor simulated (ADR-028 labels
# a *metric value*; this is synthesized text) -- it carries its own envelope
# instead: citations the caller can verify are real, plus an explicit
# evidence_sufficient flag the retrieval gate sets deterministically (DESIGN
# D2). No data_class field on this model, by design.


class KnowledgeAskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    metric_id: str | None = Field(
        default=None, description="Optional filter: only retrieve notes for this metric_id"
    )


class KnowledgeCitation(BaseModel):
    metric_id: str
    title: str
    source_url: str = Field(description="Real URL from metric_provenance -- never fabricated")


class KnowledgeAskResponse(BaseModel):
    answer: str
    citations: list[KnowledgeCitation]
    evidence_sufficient: bool
