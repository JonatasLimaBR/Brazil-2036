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
