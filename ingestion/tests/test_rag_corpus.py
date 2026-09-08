from __future__ import annotations

from pathlib import Path

import pytest
from _fakes import FakeBigQuery

from ingestion.rag_corpus import (
    fetch_current_sources,
    load_notes,
    refresh_embeddings,
    upsert_corpus,
)

CORPUS_YAML = Path(__file__).parents[1] / "data" / "rag_knowledge_corpus.yaml"


def test_load_notes_reads_real_curated_file() -> None:
    notes = load_notes(CORPUS_YAML)
    ids = {n["metric_id"] for n in notes}
    assert len(notes) == 11
    assert ids == {
        "divida_consolidada",
        "fiscal_receita",
        "fiscal_despesa",
        "fiscal_primario",
        "inss_beneficios_emitidos",
        "inss_beneficios_indeferidos",
        "pib_mensal",
        "divida_bruta_pib",
        "ipca_mensal",
        "selic_mensal",
        "cambio_usd_brl",
    }
    for note in notes:
        assert note["title"]
        assert note["body_text"]


def test_fetch_current_sources_groups_by_metric_id() -> None:
    client = FakeBigQuery(
        responder=lambda _sql: [
            {"metric_id": "pib_mensal", "source_url": "https://x", "producing_organization": "BCB"},
        ]
    )
    sources = fetch_current_sources(
        client,
        project="p",
        dataset_gold="br2036_gold",
        provenance_table="metric_provenance",
        metric_ids=["pib_mensal"],
    )
    assert sources == {"pib_mensal": ("https://x", "BCB")}
    assert "IN ('pib_mensal')" in client.queries[0]


def test_upsert_corpus_merges_and_keeps_embedding_untouched_on_match() -> None:
    client = FakeBigQuery()
    notes = load_notes(CORPUS_YAML)
    sources = {n["metric_id"]: ("https://real/" + n["metric_id"], "Org") for n in notes}

    count = upsert_corpus(
        client,
        project="p",
        dataset_gold="br2036_gold",
        table="rag_knowledge_corpus",
        notes=notes,
        sources=sources,
    )

    assert count == 11
    create_sql = client.queries[0]
    assert "CREATE TABLE IF NOT EXISTS `p.br2036_gold.rag_knowledge_corpus`" in create_sql
    merge_queries = client.queries[1:]
    assert len(merge_queries) == 11
    first_merge = merge_queries[0]
    assert "MERGE `p.br2036_gold.rag_knowledge_corpus` T USING" in first_merge
    assert "WHEN MATCHED THEN UPDATE SET title = S.title" in first_merge
    # The MATCHED branch must never touch embedding -- a text-only re-run would otherwise
    # silently wipe out an already-computed vector.
    assert "embedding = S.embedding" not in first_merge
    assert "WHEN NOT MATCHED THEN INSERT" in first_merge
    assert "NULL, CURRENT_TIMESTAMP())" in first_merge


def test_upsert_corpus_rejects_metric_id_with_no_real_provenance() -> None:
    # G6/AT5 (DEFINE/DESIGN): the corpus can only cite a source that exists for real -- a
    # curated note for a metric_id with no metric_provenance rows must fail loudly, not
    # silently skip or fall back to a placeholder URL.
    client = FakeBigQuery()
    notes = load_notes(CORPUS_YAML)

    with pytest.raises(ValueError, match="no metric_provenance rows found"):
        upsert_corpus(
            client,
            project="p",
            dataset_gold="br2036_gold",
            table="rag_knowledge_corpus",
            notes=notes,
            sources={},
        )


def test_refresh_embeddings_filters_by_array_length_not_is_null() -> None:
    # Verified live against brasil2036-dev (BUILD_REPORT): BigQuery stores a NULL
    # ARRAY<FLOAT64> as an empty array, so `embedding IS NULL` matches zero rows forever.
    client = FakeBigQuery(responder=lambda _sql: [{"n": 0}])

    pending = refresh_embeddings(
        client,
        project="p",
        dataset_gold="br2036_gold",
        table="rag_knowledge_corpus",
        connection_id="rag-vertex-ai",
        region="southamerica-east1",
    )

    assert pending == 0
    create_model_sql, update_sql, count_sql = client.queries
    assert "CREATE MODEL IF NOT EXISTS `p.br2036_gold.rag_embedding_model`" in create_model_sql
    assert "REMOTE WITH CONNECTION `p.southamerica-east1.rag-vertex-ai`" in create_model_sql
    assert "OPTIONS (ENDPOINT = 'text-embedding-005')" in create_model_sql
    for sql in (update_sql, count_sql):
        assert "embedding IS NULL" not in sql
        assert "ARRAY_LENGTH(embedding) = 0 OR ARRAY_LENGTH(embedding) IS NULL" in sql
    assert "ML.GENERATE_EMBEDDING(" in update_sql
    assert "UPDATE `p.br2036_gold.rag_knowledge_corpus` t SET embedding" in update_sql


def test_refresh_embeddings_reports_nonzero_pending() -> None:
    client = FakeBigQuery(responder=lambda _sql: [{"n": 3}])
    pending = refresh_embeddings(
        client,
        project="p",
        dataset_gold="br2036_gold",
        table="rag_knowledge_corpus",
        connection_id="rag-vertex-ai",
        region="southamerica-east1",
    )
    assert pending == 3
