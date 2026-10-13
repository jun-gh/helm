variable "project_id" {
  description = "Google Cloud Project ID"
  type        = string
}

variable "region" {
  description = "Primary GCP region (us-central1 recommended for Free Tier eligibility)"
  type        = string
  default     = "us-central1"
}

variable "firestore_location" {
  description = "Firestore location (nam5 or us-central1 for Free Tier)"
  type        = string
  default     = "nam5"
}

variable "service_name" {
  description = "Cloud Run service name for the Helm backend"
  type        = string
  default     = "helm-backend"
}

variable "container_image" {
  description = "Initial container image URI in Google Artifact Registry"
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "github_repository" {
  description = "GitHub repository in 'owner/repo' format for OIDC Workload Identity Federation"
  type        = string
}

variable "cors_origins" {
  description = "Comma-separated CORS origins allowed by the FastAPI backend"
  type        = string
  default     = "http://localhost:4200,https://helm.vercel.app"
}
