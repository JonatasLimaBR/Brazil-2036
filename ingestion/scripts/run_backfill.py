from __future__ import annotations

import argparse
import datetime as dt
import logging
import sys
import tempfile
from pathlib import Path

import requests
from google.cloud import bigquery, storage

from ingestion.backfill import run_backfill
from ingestion.ckan import CkanResource
from ingestion.connectors.base import Connector
from ingestion.connectors.inss_emitidos import InssEmitidosConnector
from ingestion.connectors.inss_indeferidos import InssIndeferidosConnector
from ingestion.connectors.inss_mantidos import InssMantidosConnector
from ingestion.pipeline_incremental import load_incremental_config

_CONFIG_ROOT = Path(__file__).resolve().parents[1] / "config"

_DATASETS: dict[str, tuple[str, type[Connector]]] = {
    "emitidos": ("inss_emitidos.yaml", InssEmitidosConnector),
    "mantidos": ("inss_mantidos.yaml", InssMantidosConnector),
    "indeferidos": ("inss_indeferidos.yaml", InssIndeferidosConnector),
}


def _indeferidos_period_resolver(session: requests.Session):
    # Indeferidos filenames carry no YYYYMM pattern at all (confirmed live
    # against the real CKAN listing: e.g. "INDEFERIDOS_JUNHO_2026.xlsx",
    # "BEN_INDEFERIDOS_082025.xlsx" -- Portuguese month names, inconsistent
    # separators, occasional MMYYYY). The file downloads once here to read the
    # true period straight from its own competencia_indeferimento column
    # (first data row, first field, e.g. "202607"), then again inside
    # pipeline_incremental.run() -- a small, deliberate double download
    # (~67 MB/month) traded for correctness over guessing from the filename.
    def resolve(resource: CkanResource) -> dt.date:
        connector = InssIndeferidosConnector(session=session, resource=resource)
        ref = connector.discover()
        with tempfile.TemporaryDirectory() as tmp:
            dest = str(Path(tmp) / "peek.csv")
            connector.download(ref, dest)
            with open(dest, encoding="utf-8") as handle:
                handle.readline()
                first_row = handle.readline()
        competencia = first_row.split(";", 1)[0].strip()
        if len(competencia) != 6 or not competencia.isdigit():
            raise ValueError(
                f"could not read a YYYYMM competencia_indeferimento from {resource.url!r} "
                f"(got {competencia!r})"
            )
        return dt.date(int(competencia[:4]), int(competencia[4:6]), 1)

    return resolve


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Run the INSS backfill for one dataset.")
    parser.add_argument("dataset", choices=sorted(_DATASETS))
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="max NOT-yet-loaded resources to process (omit for full history)",
    )
    parser.add_argument(
        "--newest-first",
        action="store_true",
        help=(
            "process the most recent resources first (CKAN lists oldest-first). "
            "Use this when older months use a different, unsupported source "
            "schema -- confirmed real for Emitidos (changed at least twice "
            "between 2023 and 2026) -- so --limit bounds recent, likely-valid "
            "months instead of guaranteed-to-fail multi-GB historical ones."
        ),
    )
    args = parser.parse_args()

    config_file, connector_cls = _DATASETS[args.dataset]
    config = load_incremental_config(_CONFIG_ROOT / config_file)

    session = requests.Session()
    bq_client = bigquery.Client(project=config.gcp_project)
    storage_client = storage.Client(project=config.gcp_project)

    def connector_factory(resource: CkanResource) -> Connector:
        return connector_cls(session=session, resource=resource)  # type: ignore[call-arg]

    kwargs = {}
    if args.dataset == "indeferidos":
        kwargs["period_resolver"] = _indeferidos_period_resolver(session)

    result = run_backfill(
        ckan_session=session,  # type: ignore[arg-type]
        config=config,
        connector_factory=connector_factory,
        storage_client=storage_client,
        bq_client=bq_client,
        limit=args.limit,
        newest_first=args.newest_first,
        **kwargs,
    )

    for outcome in result.outcomes:
        print(
            f"{outcome.resource_id}\t{outcome.reference_period}\t{outcome.status}\t{outcome.detail}"
        )
    print(
        f"\nTOTAL dataset={result.dataset_id} loaded={result.loaded} "
        f"skipped={result.skipped} failed={result.failed} "
        f"of {len(result.outcomes)} resources seen"
    )
    return 1 if result.failed else 0


if __name__ == "__main__":
    sys.exit(main())
