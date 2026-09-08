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
