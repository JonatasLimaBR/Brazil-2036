resource "google_artifact_registry_repository" "images" {
  repository_id = "br2036"
  location      = var.region
  format        = "DOCKER"
  description   = "BRASIL 2036 container images"

  depends_on = [google_project_service.enabled]
}
