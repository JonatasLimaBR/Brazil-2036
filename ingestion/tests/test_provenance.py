from __future__ import annotations

from _fakes import FakeBigQuery

from ingestion.provenance import write_from_gold


def _responder(sql: str) -> list[dict[str, object]]:
    if "COUNT(*)" in sql and "metric_provenance" in sql:
        return [{"n": 27}]
    return []


def test_write_from_gold_ddl_delete_insert_select_count() -> None:
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
    joined = "\n".join(client.queries)
    assert "CREATE TABLE IF NOT EXISTS `p.br2036_gold.metric_provenance`" in joined
    assert "DELETE FROM `p.br2036_gold.metric_provenance` WHERE reference_year = 2022" in joined
    assert "INSERT INTO `p.br2036_gold.metric_provenance`" in joined
    assert "FROM `p.br2036_gold.gold_debt_state_current` WHERE reference_year = 2022" in joined
    assert "'observed', 1.0" in joined
    assert "'run123'" in joined
