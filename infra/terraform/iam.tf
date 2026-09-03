resource "google_service_account" "ingestion_job" {
  account_id   = "ingestion-job"
  display_name = "MVP walking skeleton ingestion job runtime"
}

# Least privilege on the immutable RAW zone: create + read, never overwrite/delete.
resource "google_storage_bucket_iam_member" "job_raw_creator" {
  bucket = google_storage_bucket.raw.name
  role   = "roles/storage.objectCreator"
  member = "serviceAccount:${google_service_account.ingestion_job.email}"
}

resource "google_storage_bucket_iam_member" "job_raw_viewer" {
  bucket = google_storage_bucket.raw.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.ingestion_job.email}"
}

resource "google_project_iam_member" "job_bq_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.ingestion_job.email}"
}

resource "google_bigquery_dataset_iam_member" "job_dataset_editor" {
  for_each   = google_bigquery_dataset.layer
  dataset_id = each.value.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.ingestion_job.email}"
}

# CI (tf-deployer, via WIF) needs to build and push images and deploy the job.
data "google_project" "this" {
  project_id = var.project_id
}

resource "google_artifact_registry_repository_iam_member" "deployer_push" {
  location   = google_artifact_registry_repository.images.location
  repository = google_artifact_registry_repository.images.repository_id
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:tf-deployer@${var.project_id}.iam.gserviceaccount.com"
}
