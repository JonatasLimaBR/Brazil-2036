from __future__ import annotations

from _fakes import FakeBigQuery

from ingestion.provenance import write_from_gold


def _responder(sql: str) -> list[dict[str, object]]:
    if "COUNT(*)" in sql and "metric_provenance" in sql:
        return [{"n": 27}]
    return []


def test_write_from_gold_create_or_replace_from_gold_then_count() -> None:
    client = FakeBigQuery(_responder)
    n = write_from_gold(
        client,
        project="p",
        dataset_gold="br2036_gold",
        gold_table="gold_debt_state_current",
        provenance_table="metric_provenance",
        reference_year=2022,
        source_url="https://x/y.csv",
        silver_transform="sql/silver/debt_state.sql",
        silver_transform_version="run123",
        bronze_object="gs://p-raw/divida_estados/abc.csv",
        catalog_dataset_id="divida_consolidada_estados",
        producing_organization="COREM / STN",
        run_id="run123",
    )
    assert n == 27
    create_sql = client.queries[0]
    assert "CREATE OR REPLACE TABLE `p.br2036_gold.metric_provenance` AS SELECT" in create_sql
    assert "FROM `p.br2036_gold.gold_debt_state_current` WHERE reference_year = 2022" in create_sql
    assert "'observed' AS scenario" in create_sql and "1.0 AS confidence" in create_sql
    assert "'run123' AS run_id" in create_sql
    assert "DELETE" not in create_sql and "INSERT" not in create_sql
    assert "COUNT(*)" in client.queries[1]
