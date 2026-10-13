output "cloud_run_url" {
  description = "Public HTTPS URL of the scale-to-zero Helm Cloud Run service"
  value       = google_cloud_run_v2_service.helm_backend.uri
}

output "artifact_registry_repository" {
  description = "Google Artifact Registry Docker repository path"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.helm_repo.repository_id}"
}

output "workload_identity_provider" {
  description = "Full Workload Identity Provider resource name for GitHub Actions OIDC"
  value       = google_iam_workload_identity_pool_provider.github_provider.name
}

output "deployer_service_account_email" {
  description = "Service Account email used by GitHub Actions OIDC workflow"
  value       = google_service_account.github_deployer.email
}
