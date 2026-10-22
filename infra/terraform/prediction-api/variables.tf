variable "project_id" {
  description = "GCP project id."
  type        = string
}

variable "region" {
  description = "GCP region for Cloud Run and Artifact Registry."
  type        = string
  default     = "us-central1"
}

variable "artifact_repository_id" {
  description = "Existing Artifact Registry Docker repository id."
  type        = string
  default     = "momo-fraud"
}

variable "deploy_cloud_run" {
  description = "Set true after the API Docker image has been built and pushed."
  type        = bool
  default     = false
}

variable "container_image" {
  description = "Prediction API container image URI in Artifact Registry."
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "cloud_run_service_name" {
  description = "Cloud Run service name for the prediction API."
  type        = string
  default     = "momo-fraud-api"
}

variable "cloud_run_ingress" {
  description = "Cloud Run network ingress. Use INGRESS_TRAFFIC_ALL for the direct run.app URL."
  type        = string
  default     = "INGRESS_TRAFFIC_ALL"
}

variable "allow_unauthenticated" {
  description = "Allow public access to the prediction API. Useful for a class/demo service."
  type        = bool
  default     = true
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

variable "mlflow_tracking_uri" {
  description = "Shared MLflow tracking server URL."
  type        = string
  default     = "https://momo-mlflow-7e2lu7f7ta-uc.a.run.app"
}

variable "mlflow_experiment_name" {
  description = "MLflow experiment used by the fraud project."
  type        = string
  default     = "momo-fraud"
}

variable "mlflow_artifact_bucket_name" {
  description = "GCS bucket where MLflow stores model artifacts."
  type        = string
  default     = "momo-fraud-momo-fraud-mlflow-artifacts"
}

variable "request_log_collection" {
  description = "Firestore collection used for prediction request logs."
  type        = string
  default     = "prediction_requests"
}
