from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

_CORPUS_YAML = Path(__file__).resolve().parents[2] / "data" / "rag_knowledge_corpus.yaml"
_TEST_METRIC_IDS = ("pib_mensal", "selic_mensal")


@pytest.fixture(scope="module")
def project() -> str:
    value = os.environ.get("GCP_PROJECT")
    if not value:
        pytest.skip("GCP_PROJECT not set; integration test needs a real GCP project")
    return value


@pytest.fixture(scope="module")
def region() -> str:
    return os.environ.get("BQ_LOCATION", "southamerica-east1")


@pytest.fixture(scope="module")
def run_id() -> str:
    return os.environ.get("GITHUB_RUN_ID") or uuid.uuid4().hex[:12]


@pytest.fixture(scope="module")
def bq(project: str):  # type: ignore[no-untyped-def]
    from google.cloud import bigquery

    return bigquery.Client(project=project)


@pytest.fixture(scope="module")
def gold_dataset(bq, project: str, run_id: str, region: str) -> Iterator[str]:  # type: ignore[no-untyped-def]
    from google.cloud import bigquery

    name = f"citest_{run_id}_rag_gold"
    dataset = bigquery.Dataset(f"{project}.{name}")
    dataset.location = region
    dataset.default_table_expiration_ms = 3600 * 1000
    bq.create_dataset(dataset, exists_ok=True)
    try:
        yield name
    finally:
        bq.delete_dataset(f"{project}.{name}", delete_contents=True, not_found_ok=True)


@pytest.fixture()
def fake_provenance(bq, project: str, gold_dataset: str) -> None:  # type: ignore[no-untyped-def]
    from ingestion.bigquery_io import run_sql, sql_literal

    table = f"`{project}.{gold_dataset}.metric_provenance`"
    run_sql(
        bq,
        f"CREATE TABLE IF NOT EXISTS {table} "
        "(metric_id STRING, source STRING, producing_organization STRING)",
    )
    for metric_id in _TEST_METRIC_IDS:
        source_url = sql_literal("https://real.example/" + metric_id)
        run_sql(
            bq,
            f"INSERT INTO {table} (metric_id, source, producing_organization) "
            f"VALUES ({sql_literal(metric_id)}, {source_url}, {sql_literal('BCB')})",
        )


def test_rag_corpus_load_and_embed_against_bigquery(  # type: ignore[no-untyped-def]
    project: str, region: str, bq, gold_dataset: str, fake_provenance: None
) -> None:
    from ingestion.rag_corpus import (
        fetch_current_sources,
        load_notes,
        refresh_embeddings,
        upsert_corpus,
    )

    all_notes = load_notes(_CORPUS_YAML)
    notes = [n for n in all_notes if n["metric_id"] in _TEST_METRIC_IDS]
    assert len(notes) == len(_TEST_METRIC_IDS)

    sources = fetch_current_sources(
        bq,
        project=project,
        dataset_gold=gold_dataset,
        provenance_table="metric_provenance",
        metric_ids=[n["metric_id"] for n in notes],
    )
    assert set(sources) == set(_TEST_METRIC_IDS)

    loaded = upsert_corpus(
        bq,
        project=project,
        dataset_gold=gold_dataset,
        table="rag_knowledge_corpus",
        notes=notes,
        sources=sources,
    )
    assert loaded == len(_TEST_METRIC_IDS)

    pending = refresh_embeddings(
        bq,
        project=project,
        dataset_gold=gold_dataset,
        table="rag_knowledge_corpus",
        connection_id="rag-vertex-ai",
        region=region,
    )
    assert pending == 0

    from ingestion.bigquery_io import run_sql

    rows = run_sql(
        bq,
        f"SELECT metric_id, source_url, ARRAY_LENGTH(embedding) AS dims "
        f"FROM `{project}.{gold_dataset}.rag_knowledge_corpus` ORDER BY metric_id",
    )
    assert len(rows) == len(_TEST_METRIC_IDS)
    for row in rows:
        assert row["source_url"] == f"https://real.example/{row['metric_id']}"
        assert row["dims"] and row["dims"] > 0

    # Idempotency: a 2nd refresh over already-embedded rows must not error and must still
    # report zero pending (guards against the ARRAY_LENGTH-vs-IS NULL regression directly).
    pending_again = refresh_embeddings(
        bq,
        project=project,
        dataset_gold=gold_dataset,
        table="rag_knowledge_corpus",
        connection_id="rag-vertex-ai",
        region=region,
    )
    assert pending_again == 0
