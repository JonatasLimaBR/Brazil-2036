from __future__ import annotations

import argparse
import sys

DEFAULT_CONNECTION_ID = "rag-vertex-ai"
DEFAULT_EMBEDDING_MODEL_ENDPOINT = "text-embedding-005"
DEFAULT_MODEL_NAME = "rag_embedding_model"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "RAG_PROVENANCE_QA PR1 (DESIGN D3): verify the BigQuery<->Vertex AI connection "
            "and ML.GENERATE_EMBEDDING work for real in this project/region before any "
            "retrieval/endpoint code is written."
        )
    )
    parser.add_argument("--project", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--gold-dataset", default="br2036_gold")
    parser.add_argument("--connection-id", default=DEFAULT_CONNECTION_ID)
    parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME)
    parser.add_argument("--embedding-endpoint", default=DEFAULT_EMBEDDING_MODEL_ENDPOINT)
    args = parser.parse_args()

    from google.cloud import bigquery

    from ingestion.bigquery_io import run_sql

    client = bigquery.Client(project=args.project)
    model = f"`{args.project}.{args.gold_dataset}.{args.model_name}`"
    connection = f"`{args.project}.{args.region}.{args.connection_id}`"

    try:
        run_sql(
            client,
            f"CREATE MODEL IF NOT EXISTS {model} "
            f"REMOTE WITH CONNECTION {connection} "
            f"OPTIONS (ENDPOINT = '{args.embedding_endpoint}')",
            maximum_bytes_billed=None,
        )
    except Exception as exc:  # noqa: BLE001 -- this script's whole purpose is to report failure
        print("CREATE MODEL FAILED", file=sys.stderr)
        print(f"  {exc}", file=sys.stderr)
        return 1

    try:
        rows = run_sql(
            client,
            f"SELECT ml_generate_embedding_result AS embedding "
            f"FROM ML.GENERATE_EMBEDDING(MODEL {model}, "
            f"(SELECT 'verificacao real da conexao RAG_PROVENANCE_QA' AS content))",
            maximum_bytes_billed=None,
        )
    except Exception as exc:  # noqa: BLE001 -- this script's whole purpose is to report failure
        print("ML.GENERATE_EMBEDDING FAILED", file=sys.stderr)
        print(f"  {exc}", file=sys.stderr)
        return 1

    if not rows or not rows[0].get("embedding"):
        print("ML.GENERATE_EMBEDDING FAILED", file=sys.stderr)
        print("  query succeeded but returned no embedding vector", file=sys.stderr)
        return 1

    print(f"OK model={args.model_name} embedding_dims={len(rows[0]['embedding'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
