from __future__ import annotations

import datetime as dt

from _fakes import FakeBigQuery

from ingestion.bronze import load, load_partition


def _responder(sql: str) -> list[dict[str, object]]:
    if "COUNT(*)" in sql:
        return [{"f0_": 14}]
    return []


def test_load_partition_deletes_and_inserts_scoped_by_month() -> None:
    client = FakeBigQuery(_responder)
    result = load_partition(
        client,
        project="p",
        dataset_bronze="br2036_bronze",
        table="inss_beneficios_emitidos_raw",
        columns=("despacho", "uf", "vl_liquido"),
        field_delimiter=";",
        reference_period=dt.date(2026, 6, 1),
        raw_uri="gs://p-raw/inss_beneficios_emitidos/abc123.csv",
        source_uri="https://s3/emitidos_202606.zip",
        row_hash="abc123",
    )
    assert result.rows_loaded == 14
    create_sql, load_sql, delete_sql, insert_sql, count_sql = client.queries
    target = "`p.br2036_bronze.inss_beneficios_emitidos_raw`"
    assert f"CREATE TABLE IF NOT EXISTS {target}" in create_sql
    assert "PARTITION BY _reference_period" in create_sql
    assert "CREATE OR REPLACE" not in create_sql
    assert "LOAD DATA OVERWRITE" in load_sql and "_stg" in load_sql
    expected_scope = (
        "_reference_period = DATE('2026-06-01') AND _source_uri = 'https://s3/emitidos_202606.zip'"
    )
    assert delete_sql == f"DELETE FROM {target} WHERE {expected_scope}"
    assert f"INSERT INTO {target} SELECT" in insert_sql
    assert "despacho, uf, vl_liquido" in insert_sql
    assert "DATE('2026-06-01') AS _reference_period" in insert_sql
    assert count_sql == f"SELECT COUNT(*) FROM {target} WHERE {expected_scope}"


def test_load_partition_reruns_are_idempotent_per_month() -> None:
    client = FakeBigQuery(_responder)
    for _ in range(2):
        load_partition(
            client,
            project="p",
            dataset_bronze="br2036_bronze",
            table="inss_beneficios_emitidos_raw",
            columns=("uf",),
            field_delimiter=";",
            reference_period=dt.date(2026, 6, 1),
            raw_uri="gs://p-raw/x.csv",
            source_uri="https://s3/x.zip",
            row_hash="h1",
        )
    delete_queries = [q for q in client.queries if q.startswith("DELETE")]
    assert len(delete_queries) == 2
    assert all("2026-06-01" in q for q in delete_queries)


def test_load_partition_scopes_by_source_uri_not_just_month() -> None:
    # INSS Mantidos publishes 3 resources per month (Ativos/Suspensos/
    # Cessados) sharing the same reference_period. Loading the second
    # resource for a month must not delete the first resource's rows.
    client = FakeBigQuery(_responder)
    load_partition(
        client,
        project="p",
        dataset_bronze="br2036_bronze",
        table="inss_beneficios_mantidos_raw",
        columns=("uf",),
        field_delimiter=";",
        reference_period=dt.date(2026, 6, 1),
        raw_uri="gs://p-raw/ativos.csv",
        source_uri="https://s3/mantidos_ativos_202606.zip",
        row_hash="h-ativos",
    )
    load_partition(
        client,
        project="p",
        dataset_bronze="br2036_bronze",
        table="inss_beneficios_mantidos_raw",
        columns=("uf",),
        field_delimiter=";",
        reference_period=dt.date(2026, 6, 1),
        raw_uri="gs://p-raw/suspensos.csv",
        source_uri="https://s3/mantidos_suspensos_202606.csv",
        row_hash="h-suspensos",
    )
    delete_queries = [q for q in client.queries if q.startswith("DELETE")]
    assert len(delete_queries) == 2
    assert "mantidos_ativos_202606.zip" in delete_queries[0]
    assert "mantidos_suspensos_202606.csv" in delete_queries[1]


def test_load_default_columns_match_original_debt_shape() -> None:
    # columns/field_delimiter default to the debt dataset's original hardcoded
    # shape so this generalization is a no-op for the existing caller.
    client = FakeBigQuery(_responder)
    load(
        client,
        project="p",
        dataset_bronze="br2036_bronze",
        table="divida_estados_raw",
        raw_uri="gs://p-raw/divida_estados/abc.csv",
        source_uri="https://tesouro/x.csv",
        row_hash="abc",
    )
    load_sql, create_sql, _count_sql = client.queries
    assert "UF STRING, ANO STRING, VALOR STRING" in load_sql
    assert "field_delimiter=';'" in load_sql
    assert "SELECT UF, ANO, VALOR," in create_sql


def test_load_with_custom_columns_is_not_hardcoded_to_debt_shape() -> None:
    client = FakeBigQuery(_responder)
    load(
        client,
        project="p",
        dataset_bronze="br2036_bronze",
        table="fiscal_uniao_raw",
        raw_uri="gs://p-raw/fiscal/abc.csv",
        source_uri="https://tesouro/rtn.xlsx",
        row_hash="abc",
        columns=("metric_id", "reference_period", "value_millions"),
        field_delimiter=",",
    )
    load_sql, create_sql, _count_sql = client.queries
    assert "metric_id STRING, reference_period STRING, value_millions STRING" in load_sql
    assert "field_delimiter=','" in load_sql
    assert "SELECT metric_id, reference_period, value_millions," in create_sql
