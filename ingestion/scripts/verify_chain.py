from __future__ import annotations

import argparse
import sys

EXPECTED_ENTITIES = 27


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the provenance chain in BigQuery.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--gold-dataset", default="br2036_gold")
    parser.add_argument("--gold-table", default="gold_debt_state_current")
    parser.add_argument("--provenance-table", default="metric_provenance")
    args = parser.parse_args()

    from google.cloud import bigquery

    client = bigquery.Client(project=args.project)
    gold = f"`{args.project}.{args.gold_dataset}.{args.gold_table}`"
    prov = f"`{args.project}.{args.gold_dataset}.{args.provenance_table}`"

    row = next(
        iter(
            client.query(
                f"""
                WITH y AS (SELECT MAX(reference_year) AS ry FROM {gold})
                SELECT
                  (SELECT ry FROM y) AS reference_year,
                  (SELECT COUNT(DISTINCT state_ibge_code) FROM {gold}, y
                     WHERE reference_year = y.ry) AS gold_entities,
                  (SELECT COUNTIF(value IS NULL OR reference_date IS NULL
                     OR state_ibge_code IS NULL) FROM {gold}, y
                     WHERE reference_year = y.ry) AS gold_nulls,
                  (SELECT COUNTIF(value < 0) FROM {gold}, y
                     WHERE reference_year = y.ry) AS negatives,
                  (SELECT COUNT(*) FROM {prov}, y WHERE reference_year = y.ry) AS prov_rows
                """
            ).result()
        )
    )

    problems: list[str] = []
    if row["gold_entities"] != EXPECTED_ENTITIES:
        problems.append(f"gold has {row['gold_entities']} entities, expected {EXPECTED_ENTITIES}")
    if row["gold_nulls"]:
        problems.append(f"{row['gold_nulls']} null key/value rows in gold")
    if row["negatives"]:
        problems.append(f"{row['negatives']} negative values in gold")
    if row["prov_rows"] != row["gold_entities"]:
        problems.append(
            f"provenance coverage {row['prov_rows']} != gold rows {row['gold_entities']}"
        )

    if problems:
        print("CHAIN VERIFICATION FAILED", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    print(
        f"OK reference_year={row['reference_year']} entities={row['gold_entities']} "
        f"provenance_rows={row['prov_rows']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
