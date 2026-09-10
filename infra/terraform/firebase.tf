# RBAC_ABAC_AUTH (ADR-062): real identity provider for real user login. google_firebase_project
# links Firebase to the existing GCP project (google-beta provider -- Firebase resources aren't
# in the stable google provider yet); Identity Platform config enables email/password sign-in.
#
# Google Sign-In is deferred, not implemented here: it requires a separate resource
# (google_identity_platform_default_supported_idp_config) whose client_id/client_secret are both
# required fields that can only come from an OAuth 2.0 client created manually in the GCP Console
# -- Terraform/gcloud cannot provision that client. This is a real automation gap (confirmed via
# provider schema introspection), the same shape as the one-time manual step in scripts/bootstrap.sh.
# Follow-up: create the OAuth client by hand, then add google_identity_platform_default_supported_idp_config
# referencing it.

resource "google_firebase_project" "default" {
  provider = google-beta
  project  = var.project_id

  depends_on = [google_project_service.enabled]
}

resource "google_identity_platform_config" "default" {
  provider = google-beta
  project  = var.project_id

  sign_in {
    email {
      enabled           = true
      password_required = true
    }
  }

  depends_on = [google_firebase_project.default]
}
