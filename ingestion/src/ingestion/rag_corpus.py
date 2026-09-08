from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

import yaml

from ingestion.bigquery_io import BigQueryClient, run_sql, sql_literal

_TABLE_SCHEMA = (
    "metric_id STRING, title STRING, body_text STRING, source_url STRING, "
    "producing_organization STRING, embedding ARRAY<FLOAT64>, updated_at TIMESTAMP"
)


class CorpusNote(Mapping[str, str]):
    def __init__(self, metric_id: str, title: str, body_text: str) -> None:
        self._data = {"metric_id": metric_id, "title": title, "body_text": body_text}

    def __getitem__(self, key: str) -> str:
        return self._data[key]

    def __iter__(self):  # type: ignore[no-untyped-def]
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)


def load_notes(yaml_path: str | Path) -> list[CorpusNote]:
    with open(yaml_path, encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return [
        CorpusNote(n["metric_id"], n["title"], n["body_text"].strip()) for n in raw.get("notes", [])
    ]


def fetch_current_sources(
    client: BigQueryClient,
    *,
    project: str,
    dataset_gold: str,
    provenance_table: str,
    metric_ids: Sequence[str],
) -> dict[str, tuple[str, str]]:
    # Sourced from metric_provenance at load time, not hardcoded in the curated YAML: some
    # sources (e.g. the fiscal wide series) republish under a new filename every month, so a
    # URL baked into version-controlled text would go stale the first time that file rotates.
    prov = f"`{project}.{dataset_gold}.{provenance_table}`"
    ids_literal = ", ".join(sql_literal(m) for m in metric_ids)
    rows = run_sql(
        client,
        f"SELECT metric_id, ANY_VALUE(source) AS source_url, "
        f"ANY_VALUE(producing_organization) AS producing_organization "
        f"FROM {prov} WHERE metric_id IN ({ids_literal}) GROUP BY metric_id",
    )
    return {r["metric_id"]: (r["source_url"], r["producing_organization"]) for r in rows}


def upsert_corpus(
    client: BigQueryClient,
    *,
    project: str,
    dataset_gold: str,
    table: str,
    notes: Sequence[CorpusNote],
    sources: Mapping[str, tuple[str, str]],
) -> int:
    fq_name = f"`{project}.{dataset_gold}.{table}`"
    run_sql(client, f"CREATE TABLE IF NOT EXISTS {fq_name} ({_TABLE_SCHEMA})")

    known = [n for n in notes if n["metric_id"] in sources]
    missing = [n["metric_id"] for n in notes if n["metric_id"] not in sources]
    if missing:
        raise ValueError(
            f"no metric_provenance rows found for curated metric_id(s): {missing} -- "
            "the corpus can only cite a source that exists for real"
        )

    for note in known:
        source_url, producing_organization = sources[note["metric_id"]]
        # MERGE, not CREATE OR REPLACE (registry.py/provenance.py precedent): the UPDATE
        # branch deliberately omits `embedding` so a re-run of the curated text never wipes
        # out an already-computed vector -- the embedding refresh is a separate step
        # (ingestion/sql/gold/rag_knowledge_embeddings.sql), run after this one.
        run_sql(
            client,
            f"MERGE {fq_name} T USING "
            f"(SELECT {sql_literal(note['metric_id'])} AS metric_id, "
            f"{sql_literal(note['title'])} AS title, "
            f"{sql_literal(note['body_text'])} AS body_text, "
            f"{sql_literal(source_url)} AS source_url, "
            f"{sql_literal(producing_organization)} AS producing_organization) S "
            "ON T.metric_id = S.metric_id "
            "WHEN MATCHED THEN UPDATE SET title = S.title, body_text = S.body_text, "
            "source_url = S.source_url, producing_organization = S.producing_organization, "
            "updated_at = CURRENT_TIMESTAMP() "
            "WHEN NOT MATCHED THEN INSERT "
            "(metric_id, title, body_text, source_url, producing_organization, embedding, "
            "updated_at) "
            "VALUES (S.metric_id, S.title, S.body_text, S.source_url, S.producing_organization, "
            "NULL, CURRENT_TIMESTAMP())",
        )
    return len(known)


def refresh_embeddings(
    client: BigQueryClient,
    *,
    project: str,
    dataset_gold: str,
    table: str,
    connection_id: str,
    region: str,
    model_name: str = "rag_embedding_model",
    embedding_endpoint: str = "text-embedding-005",
) -> int:
    # Only rows without a real embedding are recomputed -- keeps this idempotent and cheap to
    # re-run after upsert_corpus() touches text without changing every row's vector.
    #
    # `ARRAY_LENGTH(embedding) = 0 OR ... IS NULL`, not `embedding IS NULL`: verified live
    # against brasil2036-dev that BigQuery silently stores a NULL ARRAY<FLOAT64> as an empty
    # array `[]`, never a true SQL NULL -- `embedding IS NULL` matches zero rows even for a
    # column that was just inserted as NULL, which would have made this refresh a silent no-op
    # forever (every row stays unembedded, no error, nothing in any mock would have caught it).
    _NEEDS_EMBEDDING = "ARRAY_LENGTH(embedding) = 0 OR ARRAY_LENGTH(embedding) IS NULL"

    fq_name = f"`{project}.{dataset_gold}.{table}`"
    model = f"`{project}.{dataset_gold}.{model_name}`"
    connection = f"`{project}.{region}.{connection_id}`"

    run_sql(
        client,
        f"CREATE MODEL IF NOT EXISTS {model} "
        f"REMOTE WITH CONNECTION {connection} "
        f"OPTIONS (ENDPOINT = {sql_literal(embedding_endpoint)})",
        maximum_bytes_billed=None,
    )
    run_sql(
        client,
        f"UPDATE {fq_name} t SET embedding = e.ml_generate_embedding_result "
        "FROM (SELECT metric_id, ml_generate_embedding_result FROM ML.GENERATE_EMBEDDING("
        f"MODEL {model}, "
        f"(SELECT metric_id, body_text AS content FROM {fq_name} WHERE {_NEEDS_EMBEDDING})"
        ")) e WHERE t.metric_id = e.metric_id",
        maximum_bytes_billed=None,
    )
    pending = run_sql(client, f"SELECT COUNT(*) AS n FROM {fq_name} WHERE {_NEEDS_EMBEDDING}")
    return int(pending[0]["n"]) if pending else 0
