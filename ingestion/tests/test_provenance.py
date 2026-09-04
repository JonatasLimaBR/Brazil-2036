from __future__ import annotations

import datetime as dt

from _fakes import FakeBigQuery

from ingestion.provenance import write_from_gold


def _responder(sql: str) -> list[dict[str, object]]:
    if "COUNT(*)" in sql and "metric_provenance" in sql:
        return [{"n": 27}]
    return []


def test_write_from_gold_deletes_and_inserts_scoped_by_metric_and_period() -> None:
    # DELETE+INSERT scoped by (metric_id, reference_date), not CREATE OR REPLACE:
    # metric_provenance is shared across every metric/period this project produces.
    client = FakeBigQuery(_responder)
    n = write_from_gold(
        client,
        project="p",
        dataset_gold="br2036_gold",
        gold_table="gold_debt_state_current",
        provenance_table="metric_provenance",
        metric_id="divida_consolidada",
        reference_date=dt.date(2022, 12, 31),
        source_url="https://x/y.csv",
        silver_transform="sql/silver/debt_state.sql",
        silver_transform_version="run123",
        bronze_object="gs://p-raw/divida_estados/abc.csv",
        catalog_dataset_id="divida_consolidada_estados",
        producing_organization="COREM / STN",
        run_id="run123",
    )
    assert n == 27
    create_sql, delete_sql, insert_sql, count_sql = client.queries
    assert "CREATE TABLE IF NOT EXISTS `p.br2036_gold.metric_provenance`" in create_sql
    scope = "metric_id = 'divida_consolidada' AND reference_date = DATE('2022-12-31')"
    assert delete_sql == f"DELETE FROM `p.br2036_gold.metric_provenance` WHERE {scope}"
    assert "INSERT INTO `p.br2036_gold.metric_provenance` SELECT" in insert_sql
    assert f"FROM `p.br2036_gold.gold_debt_state_current` WHERE {scope}" in insert_sql
    assert "EXTRACT(YEAR FROM reference_date) AS reference_year" in insert_sql
    assert "'observed' AS scenario" in insert_sql and "1.0 AS confidence" in insert_sql
    assert "'run123' AS run_id" in insert_sql
    assert "CREATE OR REPLACE" not in create_sql
    assert "CREATE OR REPLACE" not in insert_sql
    assert "COUNT(*)" in count_sql
