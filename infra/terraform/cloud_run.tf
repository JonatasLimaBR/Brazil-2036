resource "google_cloud_run_v2_job" "ingestion" {
  name     = "br2036-ingestion"
  location = var.region

  deletion_protection = false

  template {
    template {
      service_account = google_service_account.ingestion_job.email
      max_retries     = 1
      # Sized for INSS_BENEFICIOS (ADR-055): source files run up to ~1.2 GiB
      # compressed per resource (Mantidos Ativos), well above the debt
      # dataset's few KB. 3600s covers a single resource comfortably; running
      # the full historical backfill (37-108 resources per dataset) in one
      # execution will likely need this raised further, or the backfill
      # invoked resource-by-resource from outside this Job -- measure real
      # wall-clock time on the first run and revisit (DESIGN §7.4).
      timeout = "3600s"

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
            cpu    = "2"
            memory = "4Gi"
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
