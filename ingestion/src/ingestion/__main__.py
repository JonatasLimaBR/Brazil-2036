from __future__ import annotations

import json
import logging
import sys
from typing import cast

from ingestion.bigquery_io import BigQueryClient
from ingestion.config import load_config
from ingestion.pipeline import Quarantined, build_default_connector, run
from ingestion.raw import StorageClient


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    config = load_config()

    if not config.gcp_project or not config.raw_bucket:
        print("GCP_PROJECT and RAW_BUCKET must be set", file=sys.stderr)
        return 2

    import google.cloud.bigquery as bigquery
    import google.cloud.storage as storage

    try:
        result = run(
            config,
            connector=build_default_connector(config),
            storage_client=cast("StorageClient", storage.Client(project=config.gcp_project)),
            bq_client=cast("BigQueryClient", bigquery.Client(project=config.gcp_project)),
        )
    except Quarantined as exc:
        print(json.dumps({"status": "quarantined", "detail": str(exc)}))
        return 1

    print(json.dumps(result.__dict__, default=str))
    return 0 if result.status in {"ok", "no-op"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
