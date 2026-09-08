from __future__ import annotations

import argparse
import json
import logging
import sys
from functools import partial
from pathlib import Path

import requests
from google.cloud import bigquery, storage

from ingestion.connectors.bcb_sgs import BcbSgsSeries, build_default_connector, parse_to_long_csv
from ingestion.pipeline_wide_series import Quarantined, load_wide_series_config, run

_CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"

# dataset_id -> BCB SGS series code. All series share the exact same API
# shape (BcbSgsConnector, DEBTLAB_SIMULATOR DESIGN D1); only the
# code/metric_id differ. selic_mensal (4390) and cambio_usd_brl (3695) are
# monthly-grain series, not the daily variants (432, 1) -- wrong grain for
# this project's monthly pipeline (MACRO_TWIN_EXPANSION DESIGN 0.1).
_SERIES_CODES: dict[str, int] = {
    "pib_mensal": 4380,
    "divida_bruta_pib": 13762,
    "ipca_mensal": 433,
    "selic_mensal": 4390,
    "cambio_usd_brl": 3695,
}


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    parser = argparse.ArgumentParser()
    parser.add_argument("dataset_id", choices=sorted(_SERIES_CODES))
    args = parser.parse_args()

    config = load_wide_series_config(_CONFIG_DIR / f"{args.dataset_id}.yaml")

    if not config.gcp_project or not config.raw_bucket:
        print("GCP_PROJECT and RAW_BUCKET must be set", file=sys.stderr)
        return 2

    series = BcbSgsSeries(series_code=_SERIES_CODES[args.dataset_id], metric_id=args.dataset_id)
    session = requests.Session()
    connector = build_default_connector(session, series=series)

    try:
        result = run(
            config,
            connector=connector,
            storage_client=storage.Client(project=config.gcp_project),
            bq_client=bigquery.Client(project=config.gcp_project),
            parse_to_long_csv=partial(parse_to_long_csv, series_code=series.series_code),
        )
    except Quarantined as exc:
        print(json.dumps({"status": "quarantined", "detail": str(exc)}))
        return 1

    print(json.dumps(result.__dict__, default=str))
    return 0 if result.status in {"ok", "no-op"} else 1


if __name__ == "__main__":
    sys.exit(main())
