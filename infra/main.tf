locals {
  required_apis = [
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "firestore.googleapis.com",
    "secretmanager.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "sts.googleapis.com",
  ]
}

resource "google_project_service" "enabled_apis" {
  for_each           = toset(local.required_apis)
  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

# Google Artifact Registry for Cloud Run container images (with cleanup policy for Free Tier)
resource "google_artifact_registry_repository" "helm_repo" {
  location      = var.region
  repository_id = "helm"
  description   = "Helm Backend Container Registry"
  format        = "DOCKER"

  cleanup_policies {
    id     = "keep-minimum-versions"
    action = "KEEP"
    most_recent_versions {
      keep_count = 5
    }
  }

  depends_on = [google_project_service.enabled_apis]
}

# Firestore Native Database for LangGraph Agent State & Checkpoints
resource "google_firestore_database" "helm_state" {
  project                     = var.project_id
  name                        = "(default)"
  location_id                 = var.firestore_location
  type                        = "FIRESTORE_NATIVE"
  concurrency_mode            = "OPTIMISTIC"
  app_engine_integration_mode = "DISABLED"

  depends_on = [google_project_service.enabled_apis]
}

# Secret Manager containers for Neon Postgres URL and Gemini API Key
resource "google_secret_manager_secret" "database_url" {
  secret_id = "helm-database-url"
  replication {
    auto {}
  }
  depends_on = [google_project_service.enabled_apis]
}

resource "google_secret_manager_secret" "gemini_api_key" {
  secret_id = "helm-gemini-api-key"
  replication {
    auto {}
  }
  depends_on = [google_project_service.enabled_apis]
}
