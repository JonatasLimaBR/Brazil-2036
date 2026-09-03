# Cloud Run *services* (br2036-api, br2036-web) are created and updated by
# .github/workflows/api-web.yml via `gcloud run deploy` -- they carry a build-time
# image and the web service needs the API's URL, which only exists post-deploy.
# Terraform owns the API runtime identity and its least-privilege data access.

resource "google_service_account" "api" {
  account_id   = "api"
  display_name = "Metrics API runtime (read-only on Gold)"
}

resource "google_project_iam_member" "api_bq_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.api.email}"
}

resource "google_bigquery_dataset_iam_member" "api_gold_viewer" {
  dataset_id = google_bigquery_dataset.layer["gold"].dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = "serviceAccount:${google_service_account.api.email}"
}

output "api_service_account" {
  value = google_service_account.api.email
}
