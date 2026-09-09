# RBAC_ABAC_AUTH (ADR-062): realizes ADR-004. Non-HA (single primary instance, no read
# pool) -- identity/role/organization/audit data for a project at this scale, not a
# production workload that needs failover yet. Private IP only (Private Services Access,
# network.tf) -- no public IP, matching the project's no-static-key/least-exposure posture.

resource "random_password" "alloydb_initial_user" {
  length  = 32
  special = false # AlloyDB's initial_user password field rejects some special characters
}

resource "google_secret_manager_secret" "alloydb_password" {
  secret_id = "rbac-alloydb-password"

  replication {
    auto {}
  }

  depends_on = [google_project_service.enabled]
}

resource "google_secret_manager_secret_version" "alloydb_password" {
  secret      = google_secret_manager_secret.alloydb_password.id
  secret_data = random_password.alloydb_initial_user.result
}

resource "google_alloydb_cluster" "rbac" {
  cluster_id = "rbac-cluster"
  location   = var.region

  network_config {
    network = google_compute_network.rbac_vpc.id
  }

  initial_user {
    user     = "postgres"
    password = random_password.alloydb_initial_user.result
  }

  depends_on = [google_service_networking_connection.psa]
}

resource "google_alloydb_instance" "rbac_primary" {
  cluster           = google_alloydb_cluster.rbac.name
  instance_id       = "rbac-primary"
  instance_type     = "PRIMARY"
  availability_type = "ZONAL" # non-HA, explicit (D1) -- REGIONAL doubles compute cost

  machine_config {
    cpu_count = 2
  }
}

output "alloydb_cluster_name" {
  value = google_alloydb_cluster.rbac.name
}

output "alloydb_primary_ip" {
  value = google_alloydb_instance.rbac_primary.ip_address
}
