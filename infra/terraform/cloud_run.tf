resource "google_cloud_run_v2_job" "ingestion" {
  name     = "br2036-ingestion"
  location = var.region

  deletion_protection = false

  template {
    template {
      service_account = google_service_account.ingestion_job.email
      max_retries     = 1
      timeout         = "900s"

      containers {
        # Placeholder so the Job can be created before the first image build.
        # The data workflow replaces it via `gcloud run jobs deploy` (ignore_changes below).
        image = "us-docker.pkg.dev/cloudrun/container/job:latest"

        env {
          name  = "GCP_PROJECT"
          value = var.project_id
        }
        env {
          name  = "RAW_BUCKET"
          value = google_storage_bucket.raw.name
        }
        resources {
          limits = {
            cpu    = "1"
            memory = "512Mi"
          }
        }
      }
    }
  }

  lifecycle {
    ignore_changes = [template[0].template[0].containers[0].image]
  }

  depends_on = [google_project_service.enabled]
}
