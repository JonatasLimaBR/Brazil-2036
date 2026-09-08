from __future__ import annotations

import uuid
from datetime import UTC, datetime
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.bigquery_repo import BigQueryRepo, build_bigquery_run_query
from api.config import Config, load_config
from api.knowledge import GenerateContent, build_genai_generate, compose_answer, retrieve
from api.models import (
    DebtLabScenarioBase,
    DebtLabScenarioRequest,
    DebtLabScenarioResponse,
    KnowledgeAskRequest,
    KnowledgeAskResponse,
    MetricResponse,
    NationalMetricResponse,
    ProvenanceResponse,
    SuggestedAssumptionsResponse,
    YearlyDeterministic,
    YearlyPercentiles,
)
from api.simulators.debtlab import ENGINE_VERSION, Assumptions, project_deterministic
from api.simulators.monte_carlo import AssumptionDistribution, run_monte_carlo

app = FastAPI(
    title="BRASIL 2036 — Metrics API",
    version="1.0.0",
    description="Walking skeleton: consolidated state debt with full provenance (SPEC-033).",
)

# Public API (ADR-044): any origin may read. POST is scoped to the DebtLab
# scenario route only (ADR-059) -- still no auth (RBAC/ABAC is a later,
# separate slice), but this is the API's first mutating endpoint, so the
# route itself bounds n_iterations/horizon_years defensively (models.py).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@lru_cache
def get_config() -> Config:
    return load_config()


@lru_cache
def get_repo() -> BigQueryRepo:
    config = get_config()
    return BigQueryRepo(config, build_bigquery_run_query(config.gcp_project))


@lru_cache
def get_genai_generate() -> GenerateContent:
    config = get_config()
    return build_genai_generate(config.gcp_project, config.gcp_region)


RepoDep = Annotated[BigQueryRepo, Depends(get_repo)]
ConfigDep = Annotated[Config, Depends(get_config)]
GenAIDep = Annotated[GenerateContent, Depends(get_genai_generate)]


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


@app.get("/v1/metrics/{metric_id}/national", response_model=NationalMetricResponse)
def get_national_metric(
    metric_id: str,
    repo: RepoDep,
    config: ConfigDep,
) -> NationalMetricResponse:
    gold_table = config.metric_tables.get(metric_id)
    if gold_table is None:
        raise HTTPException(status_code=404, detail="metric not found")
    result = repo.latest_national_total(metric_id, gold_table)
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


@app.post("/v1/simulations/debtlab", response_model=DebtLabScenarioResponse)
def create_debtlab_scenario(
    request: DebtLabScenarioRequest,
    repo: RepoDep,
) -> DebtLabScenarioResponse:
    # SPEC-010: the engine reads the real, observed divida/PIB anchor -- it
    # never invents a starting point (ADR-012).
    base = repo.debtlab_base()
    if base is None:
        raise HTTPException(status_code=503, detail="divida_bruta_pib base data not available yet")

    deterministic = project_deterministic(
        base.value,
        request.horizon_years,
        Assumptions(
            juros_nominal=request.juros_nominal.mean,
            crescimento_nominal_pib=request.crescimento_nominal_pib.mean,
            primario_pct_pib=request.primario_pct_pib.mean,
        ),
    )
    percentiles = run_monte_carlo(
        base_ratio_pct=base.value,
        horizon_years=request.horizon_years,
        juros=AssumptionDistribution(
            mean=request.juros_nominal.mean, std=request.juros_nominal.std
        ),
        crescimento=AssumptionDistribution(
            mean=request.crescimento_nominal_pib.mean, std=request.crescimento_nominal_pib.std
        ),
        primario=AssumptionDistribution(
            mean=request.primario_pct_pib.mean, std=request.primario_pct_pib.std
        ),
        n_iterations=request.n_iterations,
        seed=request.seed,
    )

    scenario = DebtLabScenarioResponse(
        scenario_id=uuid.uuid4().hex,
        created_at=datetime.now(UTC).isoformat(),
        horizon_years=request.horizon_years,
        base=DebtLabScenarioBase(
            reference_date=base.reference_date,
            divida_pib_pct=base.value,
            source=base.provenance.source,
        ),
        assumptions=request,
        engine_version=ENGINE_VERSION,
        seed=request.seed,
        n_iterations=request.n_iterations,
        deterministic_trajectory=[
            YearlyDeterministic(year_offset=p.year_offset, divida_pib_pct=p.divida_pib_pct)
            for p in deterministic
        ],
        percentiles=[
            YearlyPercentiles(
                year_offset=p.year_offset, p10=p.p10, p25=p.p25, p50=p.p50, p75=p.p75, p90=p.p90
            )
            for p in percentiles
        ],
    )
    repo.create_debtlab_scenario(scenario)
    return scenario


@app.get(
    "/v1/simulations/debtlab/suggested-assumptions", response_model=SuggestedAssumptionsResponse
)
def get_suggested_assumptions(repo: RepoDep) -> SuggestedAssumptionsResponse:
    # Registered before /v1/simulations/debtlab/{scenario_id} -- FastAPI
    # matches routes in registration order, and a literal path segment must
    # come first or "suggested-assumptions" would be swallowed as a
    # scenario_id by the parameterized route below.
    result = repo.suggested_assumptions()
    if result is None:
        raise HTTPException(
            status_code=503, detail="not enough real trailing data yet (need >= 12 months)"
        )
    return result


@app.get("/v1/simulations/debtlab/{scenario_id}", response_model=DebtLabScenarioResponse)
def get_debtlab_scenario(scenario_id: str, repo: RepoDep) -> DebtLabScenarioResponse:
    result = repo.get_debtlab_scenario(scenario_id)
    if result is None:
        raise HTTPException(status_code=404, detail="scenario not found")
    return result


@app.post("/v1/knowledge/ask", response_model=KnowledgeAskResponse)
def ask_knowledge(
    request: KnowledgeAskRequest,
    repo: RepoDep,
    config: ConfigDep,
    generate: GenAIDep,
) -> KnowledgeAskResponse:
    # RAG_PROVENANCE_QA (ADR-061, SPEC-018): read-only, classed READ
    # (AGENTS.md) -- retrieval decides evidence sufficiency deterministically
    # before the model is ever called (knowledge.py::compose_answer).
    notes = retrieve(
        repo.run_query, config, question=request.question, metric_id_filter=request.metric_id
    )
    return compose_answer(request.question, notes, config, generate=generate)
