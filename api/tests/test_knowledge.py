from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from api.config import Config
from api.knowledge import RetrievedNote, compose_answer, retrieve

CONFIG = Config(
    gcp_project="brasil2036-dev",
    bq_dataset_gold="br2036_gold",
    gold_table="gold_debt_state_current",
    provenance_table="metric_provenance",
    default_metric_id="divida_consolidada",
    default_state_ibge_code="35",
    rag_similarity_threshold=0.45,
)


def test_retrieve_builds_vector_search_with_params_and_parses_rows() -> None:
    captured: dict[str, Any] = {}

    def run_query(sql: str, params: Mapping[str, Any]) -> list[dict[str, Any]]:
        captured["sql"] = sql
        captured["params"] = dict(params)
        return [
            {
                "metric_id": "selic_mensal",
                "title": "Taxa Selic",
                "body_text": "texto",
                "source_url": "https://real/selic",
                "distance": 0.3016,
            }
        ]

    notes = retrieve(run_query, CONFIG, question="quanto e a selic?", metric_id_filter=None)

    assert captured["params"] == {
        "question": "quanto e a selic?",
        "top_k": CONFIG.rag_top_k,
        "metric_id_filter": None,
    }
    assert "VECTOR_SEARCH(" in captured["sql"]
    assert "ML.GENERATE_EMBEDDING(" in captured["sql"]
    filter_clause = "WHERE @metric_id_filter IS NULL OR base.metric_id = @metric_id_filter"
    assert filter_clause in captured["sql"]
    assert notes == [
        RetrievedNote(
            metric_id="selic_mensal",
            title="Taxa Selic",
            body_text="texto",
            source_url="https://real/selic",
            distance=0.3016,
        )
    ]


def test_retrieve_passes_metric_id_filter_through() -> None:
    captured: dict[str, Any] = {}

    def run_query(sql: str, params: Mapping[str, Any]) -> list[dict[str, Any]]:
        captured["params"] = dict(params)
        return []

    retrieve(run_query, CONFIG, question="x", metric_id_filter="pib_mensal")
    assert captured["params"]["metric_id_filter"] == "pib_mensal"


_RELEVANT = RetrievedNote(
    metric_id="selic_mensal",
    title="Taxa Selic",
    body_text="texto real",
    source_url="https://real/selic",
    distance=0.30,
)
_IRRELEVANT = RetrievedNote(
    metric_id="cambio_usd_brl",
    title="Cambio",
    body_text="outro texto",
    source_url="https://real/cambio",
    distance=0.60,
)


def test_compose_answer_never_calls_llm_when_no_note_is_relevant() -> None:
    def generate(*, model: str, prompt: str) -> str:
        raise AssertionError("LLM must not be called when evidence is insufficient")

    result = compose_answer("pergunta", [_IRRELEVANT], CONFIG, generate=generate)

    assert result.evidence_sufficient is False
    assert result.citations == []
    assert "insuficiente" in result.answer.lower()


def test_compose_answer_calls_llm_only_with_relevant_notes_and_cites_them() -> None:
    calls: list[str] = []

    def generate(*, model: str, prompt: str) -> str:
        calls.append(prompt)
        assert "selic_mensal" in prompt
        assert "cambio_usd_brl" not in prompt  # the irrelevant note never reaches the prompt
        assert model == CONFIG.rag_generative_model
        return "resposta real citando [selic_mensal]"

    result = compose_answer("pergunta", [_RELEVANT, _IRRELEVANT], CONFIG, generate=generate)

    assert len(calls) == 1
    assert result.evidence_sufficient is True
    assert result.answer == "resposta real citando [selic_mensal]"
    assert len(result.citations) == 1
    assert result.citations[0].metric_id == "selic_mensal"
    assert result.citations[0].source_url == "https://real/selic"


def test_compose_answer_citations_only_from_relevant_never_fabricated() -> None:
    # G6/AT5: every citation must trace back to a note the retrieval actually
    # returned -- assert this by construction, not just by trusting the model.
    def generate(*, model: str, prompt: str) -> str:
        return "x"

    result = compose_answer("q", [_RELEVANT], CONFIG, generate=generate)
    cited_urls = {c.source_url for c in result.citations}
    assert cited_urls <= {_RELEVANT.source_url}


@pytest.mark.parametrize("distance", [0.45, 0.449999])
def test_compose_answer_threshold_is_inclusive_at_the_boundary(distance: float) -> None:
    note = RetrievedNote(
        metric_id="x", title="t", body_text="b", source_url="https://real/x", distance=distance
    )

    def generate(*, model: str, prompt: str) -> str:
        return "ok"

    result = compose_answer("q", [note], CONFIG, generate=generate)
    assert result.evidence_sufficient is True
