from __future__ import annotations

from pathlib import Path

import pytest

from ingestion.sql_render import MissingPlaceholder, render, render_file

SQL_DIR = Path(__file__).parents[1] / "sql"

PLACEHOLDERS = {
    "project": "brasil2036-dev",
    "bq_dataset_control": "br2036_control",
    "bq_dataset_bronze": "br2036_bronze",
    "bq_dataset_silver": "br2036_silver",
    "bq_dataset_gold": "br2036_gold",
    "bronze_table": "debt_state_raw",
    "silver_table": "debt_state",
    "gold_table": "gold_debt_state_current",
    "uf_ibge_table": "uf_ibge",
    "metric_id": "divida_consolidada",
    "unit": "BRL",
    "data_class": "observed",
}


def test_render_substitutes() -> None:
    assert render("a ${x} b", {"x": "1"}) == "a 1 b"


def test_render_missing_raises() -> None:
    with pytest.raises(MissingPlaceholder):
        render("${a} ${b}", {"a": "1"})


def test_silver_sql_renders_without_placeholders_left() -> None:
    out = render_file(SQL_DIR / "silver" / "debt_state.sql", PLACEHOLDERS)
    assert "${" not in out
    assert "br2036_silver.debt_state" in out
    assert "DATE(CAST(b.ANO AS INT64), 12, 31)" in out


def test_gold_sql_renders_metric_id() -> None:
    out = render_file(SQL_DIR / "gold" / "gold_debt_state_current.sql", PLACEHOLDERS)
    assert "${" not in out
    assert "'divida_consolidada' AS metric_id" in out
    assert "reference_year" in out
