# RAG_PROVENANCE_QA (ADR-061): lets BigQuery remote models (ML.GENERATE_EMBEDDING) call
# Vertex AI. The connection's own service account -- not the querying principal -- is what
# calls Vertex AI, so this is the only new IAM grant this PR needs (DESIGN §3 D3: isolated
# infra spike, verified live before any pipeline/API code is written).

resource "google_bigquery_connection" "vertex_ai" {
  connection_id = "rag-vertex-ai"
  location      = var.region
  cloud_resource {}

  depends_on = [google_project_service.enabled]
}

resource "google_project_iam_member" "vertex_ai_connection_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_bigquery_connection.vertex_ai.cloud_resource[0].service_account_id}"
}

output "rag_vertex_ai_connection_id" {
  value = google_bigquery_connection.vertex_ai.name
}
