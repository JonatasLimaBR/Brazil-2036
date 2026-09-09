# Cloud Run *services* (br2036-api, br2036-web) are created and updated by
# .github/workflows/api-web.yml via `gcloud run deploy` -- they carry a build-time
# image and the web service needs the API's URL, which only exists post-deploy.
# Terraform owns the API runtime identity and its least-privilege data access.

resource "google_service_account" "api" {
  account_id   = "api-runtime"
  display_name = "Metrics API runtime (read-only on Gold, write on control/debtlab_scenarios)"
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

# ADR-059: DebtLab is the API's first write path. Scoped to the control
# dataset only (least privilege, same principle as the ingestion job's
# dataEditor grant) -- the API still cannot write to Gold/Silver/Bronze.
resource "google_bigquery_dataset_iam_member" "api_control_editor" {
  dataset_id = google_bigquery_dataset.layer["control"].dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.api.email}"
}

# RAG_PROVENANCE_QA (ADR-061): POST /v1/knowledge/ask calls Gemini directly
# via google-genai (Vertex AI backend) to synthesize an answer from notes the
# retrieval gate already validated as relevant -- this is a separate call
# from the BigQuery-internal ML.GENERATE_EMBEDDING (which authenticates as
# the bigquery_connection_vertex.tf connection's own service account, not
# api-runtime). Project-level, not dataset-scoped: aiplatform.user has no
# per-resource scoping in this project the way BigQuery dataset roles do.
resource "google_project_iam_member" "api_vertex_ai_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.api.email}"
}

# Real production 500, found live on the first POST /v1/knowledge/ask call
# after deploy: aiplatform.user alone is not enough. Every query api-runtime
# runs through knowledge.py::retrieve() references the rag-vertex-ai
# connection (ML.GENERATE_EMBEDDING on the question text) -- BigQuery
# requires the *querying* principal to also hold bigquery.connections.use on
# that specific connection resource, separate from the connection's own
# service account being allowed to call Vertex AI (bigquery_connection_vertex.tf).
resource "google_bigquery_connection_iam_member" "api_rag_connection_user" {
  project       = var.project_id
  location      = google_bigquery_connection.vertex_ai.location
  connection_id = google_bigquery_connection.vertex_ai.connection_id
  role          = "roles/bigquery.connectionUser"
  member        = "serviceAccount:${google_service_account.api.email}"
}

output "api_service_account" {
  value = google_service_account.api.email
}
