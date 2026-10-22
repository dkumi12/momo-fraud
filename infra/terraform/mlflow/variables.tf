variable "project_id" {
  description = "GCP project id."
  type        = string
}

variable "region" {
  description = "GCP region for Cloud Run, Cloud SQL, Artifact Registry, and Storage."
  type        = string
  default     = "us-central1"
}

variable "artifact_repository_id" {
  description = "Artifact Registry Docker repository id."
  type        = string
  default     = "momo-fraud"
}

variable "artifact_bucket_name" {
  description = "Optional exact GCS bucket name for MLflow artifacts. Defaults to PROJECT_ID-momo-fraud-mlflow-artifacts."
  type        = string
  default     = null
}

variable "force_destroy_bucket" {
  description = "Allow Terraform destroy to remove the artifact bucket and objects. Keep false for real work."
  type        = bool
  default     = false
}

variable "cloud_sql_tier" {
  description = "Cloud SQL machine tier."
  type        = string
  default     = "db-custom-1-3840"
}

variable "cloud_sql_disk_size_gb" {
  description = "Cloud SQL SSD disk size."
  type        = number
  default     = 20
}

variable "cloud_sql_availability_type" {
  description = "Cloud SQL availability type: ZONAL for lower cost or REGIONAL for HA."
  type        = string
  default     = "ZONAL"
}

variable "cloud_sql_ipv4_enabled" {
  description = "Enable Cloud SQL public IPv4. Required unless private IP or PSC is configured."
  type        = bool
  default     = true
}

variable "deletion_protection" {
  description = "Protect the Cloud SQL instance from accidental deletion."
  type        = bool
  default     = true
}

variable "deploy_cloud_run" {
  description = "Set true after the MLflow Docker image has been built and pushed."
  type        = bool
  default     = false
}

variable "container_image" {
  description = "MLflow container image URI in Artifact Registry."
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "cloud_run_service_name" {
  description = "Cloud Run service name."
  type        = string
  default     = "momo-mlflow"
}

variable "cloud_run_cpu" {
  description = "Cloud Run CPU limit."
  type        = string
  default     = "1"
}

variable "cloud_run_memory" {
  description = "Cloud Run memory limit."
  type        = string
  default     = "2Gi"
}

variable "cloud_run_max_instances" {
  description = "Maximum Cloud Run instances."
  type        = number
  default     = 3
}

variable "allow_unauthenticated" {
  description = "Allow public access to MLflow. Keep false unless this is a short-lived demo."
  type        = bool
  default     = false
}

variable "cloud_run_ingress" {
  description = "Cloud Run network ingress. Use INGRESS_TRAFFIC_ALL for the direct run.app URL."
  type        = string
  default     = "INGRESS_TRAFFIC_ALL"
}
