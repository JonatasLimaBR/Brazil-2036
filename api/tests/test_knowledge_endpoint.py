from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api.bigquery_repo import BigQueryRepo
from api.config import Config
from api.main import app, get_config, get_genai_generate, get_repo

CONFIG = Config(
    gcp_project="brasil2036-dev",
    bq_dataset_gold="br2036_gold",
    gold_table="gold_debt_state_current",
    provenance_table="metric_provenance",
    default_metric_id="divida_consolidada",
    default_state_ibge_code="35",
    rag_similarity_threshold=0.45,
)

_RELEVANT_ROW = {
    "metric_id": "selic_mensal",
    "title": "Taxa Selic",
    "body_text": "texto real",
    "source_url": "https://real/selic",
    "distance": 0.30,
}


def _run_query_relevant(sql: str, params: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [dict(_RELEVANT_ROW)]


def _run_query_empty(sql: str, params: Mapping[str, Any]) -> list[dict[str, Any]]:
    return []


def _fake_generate(*, model: str, prompt: str) -> str:
    return "resposta sintetizada citando [selic_mensal]"


def _client(*, run_query, generate=_fake_generate) -> TestClient:  # type: ignore[no-untyped-def]
    app.dependency_overrides[get_config] = lambda: CONFIG
    app.dependency_overrides[get_repo] = lambda: BigQueryRepo(CONFIG, run_query)
    app.dependency_overrides[get_genai_generate] = lambda: generate
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def test_ask_returns_answer_with_real_citation() -> None:
    resp = _client(run_query=_run_query_relevant).post(
        "/v1/knowledge/ask", json={"question": "quanto e a selic?"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["evidence_sufficient"] is True
    assert body["citations"] == [
        {"metric_id": "selic_mensal", "title": "Taxa Selic", "source_url": "https://real/selic"}
    ]
    assert body["answer"] == "resposta sintetizada citando [selic_mensal]"


def test_ask_returns_insufficient_evidence_without_calling_llm() -> None:
    def generate(*, model: str, prompt: str) -> str:
        raise AssertionError("LLM must not be called when retrieval found nothing")

    resp = _client(run_query=_run_query_empty, generate=generate).post(
        "/v1/knowledge/ask", json={"question": "qualquer coisa fora do corpus"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["evidence_sufficient"] is False
    assert body["citations"] == []


def test_ask_rejects_empty_question() -> None:
    resp = _client(run_query=_run_query_relevant).post("/v1/knowledge/ask", json={"question": ""})
    assert resp.status_code == 422


def test_ask_passes_metric_id_filter_through_to_retrieval() -> None:
    captured: dict[str, Any] = {}

    def run_query(sql: str, params: Mapping[str, Any]) -> list[dict[str, Any]]:
        captured["params"] = dict(params)
        return [dict(_RELEVANT_ROW)]

    resp = _client(run_query=run_query).post(
        "/v1/knowledge/ask", json={"question": "quanto e a selic?", "metric_id": "selic_mensal"}
    )
    assert resp.status_code == 200
    assert captured["params"]["metric_id_filter"] == "selic_mensal"


def test_openapi_has_knowledge_ask_path() -> None:
    schema = app.openapi()
    assert "/v1/knowledge/ask" in schema["paths"]
