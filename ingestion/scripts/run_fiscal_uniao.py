from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import requests
from google.cloud import bigquery, storage

from ingestion.connectors.fiscal_uniao import build_default_connector, parse_to_long_csv
from ingestion.pipeline_wide_series import Quarantined, load_wide_series_config, run

_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "fiscal_uniao.yaml"


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    config = load_wide_series_config(_CONFIG_PATH)

    if not config.gcp_project or not config.raw_bucket:
        print("GCP_PROJECT and RAW_BUCKET must be set", file=sys.stderr)
        return 2

    session = requests.Session()
    connector = build_default_connector(
        session, ckan_base_url=config.ckan_base_url, ckan_package_id=config.ckan_package_id
    )

    try:
        result = run(
            config,
            connector=connector,
            storage_client=storage.Client(project=config.gcp_project),
            bq_client=bigquery.Client(project=config.gcp_project),
            parse_to_long_csv=parse_to_long_csv,
        )
    except Quarantined as exc:
        print(json.dumps({"status": "quarantined", "detail": str(exc)}))
        return 1

    print(json.dumps(result.__dict__, default=str))
    return 0 if result.status in {"ok", "no-op"} else 1


if __name__ == "__main__":
    sys.exit(main())
