locals {
  bq_datasets = {
    control = "Registry, reference tables and run bookkeeping"
    bronze  = "Source-shaped ingestion"
    silver  = "Typed and standardized"
    gold    = "Canonical data products and provenance"
  }
}

resource "google_bigquery_dataset" "layer" {
  for_each                   = local.bq_datasets
  dataset_id                 = "br2036_${each.key}"
  location                   = var.region
  description                = each.value
  delete_contents_on_destroy = false

  depends_on = [google_project_service.enabled]
}
