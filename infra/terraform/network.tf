# RBAC_ABAC_AUTH (ADR-062): first VPC this project provisions. AlloyDB requires Private
# Services Access (a VPC peering to Google's managed-services network) -- BigQuery,
# Cloud Run, and every other resource so far needed no VPC of their own.

resource "google_compute_network" "rbac_vpc" {
  name                    = "rbac-vpc"
  auto_create_subnetworks = false

  depends_on = [google_project_service.enabled]
}

# /26 is the minimum Cloud Run Direct VPC egress accepts (DESIGN §0) -- this subnet only
# carries the API's outbound calls to AlloyDB's private IP, not general traffic.
resource "google_compute_subnetwork" "rbac_subnet" {
  name          = "rbac-subnet"
  network       = google_compute_network.rbac_vpc.id
  region        = var.region
  ip_cidr_range = "10.10.0.0/26"
}

resource "google_compute_global_address" "private_services_range" {
  name          = "rbac-psa-range"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.rbac_vpc.id
}

resource "google_service_networking_connection" "psa" {
  network                 = google_compute_network.rbac_vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_services_range.name]
}

output "rbac_vpc_network" {
  value = google_compute_network.rbac_vpc.name
}

output "rbac_vpc_subnet" {
  value = google_compute_subnetwork.rbac_subnet.name
}
