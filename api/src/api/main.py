from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.bigquery_repo import BigQueryRepo, build_bigquery_run_query
from api.config import Config, load_config
from api.models import MetricResponse, ProvenanceResponse

app = FastAPI(
    title="BRASIL 2036 — Metrics API",
    version="1.0.0",
    description="Walking skeleton: consolidated state debt with full provenance (SPEC-033).",
)

# Public, read-only open-data API (ADR-044): any origin may read.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@lru_cache
def get_config() -> Config:
    return load_config()


@lru_cache
def get_repo() -> BigQueryRepo:
    config = get_config()
    return BigQueryRepo(config, build_bigquery_run_query(config.gcp_project))


RepoDep = Annotated[BigQueryRepo, Depends(get_repo)]
ConfigDep = Annotated[Config, Depends(get_config)]


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/metrics/{metric_id}", response_model=MetricResponse)
def get_metric(
    metric_id: str,
    repo: RepoDep,
    config: ConfigDep,
    state_ibge_code: str | None = None,
) -> MetricResponse:
    state = state_ibge_code or config.default_state_ibge_code
    result = repo.latest_metric(metric_id, state)
    if result is None:
        raise HTTPException(status_code=404, detail="metric not found")
    return result


@app.get("/v1/provenance/{metric_id}", response_model=ProvenanceResponse)
def get_provenance(
    metric_id: str,
    repo: RepoDep,
    config: ConfigDep,
    state_ibge_code: str | None = None,
) -> ProvenanceResponse:
    state = state_ibge_code or config.default_state_ibge_code
    result = repo.provenance(metric_id, state)
    if result is None:
        raise HTTPException(status_code=404, detail="provenance not found")
    return result
