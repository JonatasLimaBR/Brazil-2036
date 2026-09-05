from __future__ import annotations

from pathlib import Path

from ingestion.pipeline_incremental import load_incremental_config

_CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"


def test_all_real_inss_configs_resolve_an_existing_contract_path() -> None:
    # Regression: _REPO_INGESTION_ROOT once pointed one directory too high
    # (ingestion/src instead of ingestion/), so the contract_path fallback
    # silently resolved to a path that never existed -- caught only by an
    # actual run against real GCP, not by any prior unit test, because none
    # asserted contract_path.exists(). This checks the real repo layout, not
    # a synthetic tmp_path fixture, precisely so it can't pass by accident.
    for config_file in sorted(_CONFIG_DIR.glob("inss_*.yaml")):
        config = load_incremental_config(config_file)
        assert config.contract_path.exists(), (
            f"{config_file.name}: contract_path {config.contract_path} does not exist"
        )
