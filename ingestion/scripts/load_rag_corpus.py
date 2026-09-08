from __future__ import annotations

import argparse
import sys
from pathlib import Path

_DEFAULT_YAML = Path(__file__).resolve().parents[1] / "data" / "rag_knowledge_corpus.yaml"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Load the curated RAG methodology corpus and refresh its embeddings."
    )
    parser.add_argument("--project", required=True)
    parser.add_argument("--region", default="southamerica-east1")
    parser.add_argument("--gold-dataset", default="br2036_gold")
    parser.add_argument("--corpus-table", default="rag_knowledge_corpus")
    parser.add_argument("--provenance-table", default="metric_provenance")
    parser.add_argument("--connection-id", default="rag-vertex-ai")
    parser.add_argument("--yaml-path", default=str(_DEFAULT_YAML))
    args = parser.parse_args()

    from google.cloud import bigquery

    from ingestion.rag_corpus import (
        fetch_current_sources,
        load_notes,
        refresh_embeddings,
        upsert_corpus,
    )

    client = bigquery.Client(project=args.project)
    notes = load_notes(args.yaml_path)
    if not notes:
        print("no notes found in YAML corpus", file=sys.stderr)
        return 2

    sources = fetch_current_sources(
        client,
        project=args.project,
        dataset_gold=args.gold_dataset,
        provenance_table=args.provenance_table,
        metric_ids=[n["metric_id"] for n in notes],
    )
    loaded = upsert_corpus(
        client,
        project=args.project,
        dataset_gold=args.gold_dataset,
        table=args.corpus_table,
        notes=notes,
        sources=sources,
    )
    pending = refresh_embeddings(
        client,
        project=args.project,
        dataset_gold=args.gold_dataset,
        table=args.corpus_table,
        connection_id=args.connection_id,
        region=args.region,
    )
    print(f"loaded={loaded} pending_embeddings={pending}")
    return 0 if pending == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
