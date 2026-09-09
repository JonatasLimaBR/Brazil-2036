from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.integration

# Exercises the full RAG_PROVENANCE_QA path against the real, already-populated
# corpus (ingestion PR2) and the real Vertex AI connection (PR1): VECTOR_SEARCH,
# the similarity gate, and a real Gemini call -- read-only, no side effects, no
# isolated dataset needed (mirrors MACRO_TWIN_EXPANSION's suggested-assumptions
# integration test, which established this pattern for api/).


@pytest.fixture(scope="module")
def project() -> str:
    value = os.environ.get("GCP_PROJECT")
    if not value:
        pytest.skip("GCP_PROJECT not set; integration test needs a real GCP project")
    return value


def _config(project: str):  # type: ignore[no-untyped-def]
    from api.config import Config

    return Config(
        gcp_project=project,
        bq_dataset_gold="br2036_gold",
        gold_table="gold_debt_state_current",
        provenance_table="metric_provenance",
        default_metric_id="divida_consolidada",
        default_state_ibge_code="35",
    )


def test_retrieve_finds_the_real_relevant_note_for_a_real_question(project: str) -> None:
    from api.bigquery_repo import build_bigquery_run_query
    from api.knowledge import retrieve

    config = _config(project)
    run_query = build_bigquery_run_query(project)

    notes = retrieve(
        run_query,
        config,
        question="por que a divida bruta do governo geral e calculada assim?",
    )

    assert notes
    assert notes[0].metric_id == "divida_bruta_pib"
    assert notes[0].distance < config.rag_similarity_threshold
    assert notes[0].source_url.startswith("https://api.bcb.gov.br/")


def test_retrieve_returns_no_note_close_enough_for_an_unrelated_question(project: str) -> None:
    from api.bigquery_repo import build_bigquery_run_query
    from api.knowledge import retrieve

    config = _config(project)
    run_query = build_bigquery_run_query(project)

    notes = retrieve(run_query, config, question="como fazer um bolo de chocolate?")

    assert all(n.distance > config.rag_similarity_threshold for n in notes)


def test_ask_knowledge_full_pipeline_cites_a_real_source(project: str) -> None:
    from api.bigquery_repo import build_bigquery_run_query
    from api.knowledge import build_genai_generate, compose_answer, retrieve

    config = _config(project)
    run_query = build_bigquery_run_query(project)
    generate = build_genai_generate(project, config.gcp_region)

    notes = retrieve(run_query, config, question="quanto e a taxa selic?")
    result = compose_answer("quanto e a taxa selic?", notes, config, generate=generate)

    assert result.evidence_sufficient is True
    assert result.answer
    assert any(c.metric_id == "selic_mensal" for c in result.citations)
    for citation in result.citations:
        assert citation.source_url.startswith("https://")
