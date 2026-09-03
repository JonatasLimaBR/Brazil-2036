output "raw_bucket" {
  value = google_storage_bucket.raw.name
}

output "bq_datasets" {
  value = { for k, v in google_bigquery_dataset.layer : k => v.dataset_id }
}

output "artifact_repo" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.images.repository_id}"
}

output "ingestion_job" {
  value = google_cloud_run_v2_job.ingestion.name
}

output "ingestion_job_sa" {
  value = google_service_account.ingestion_job.email
}
