variable "project_id" {
  description = "GCP project id."
  type        = string
}

variable "region" {
  description = "GCP region for Cloud Run Jobs and Artifact Registry."
  type        = string
  default     = "us-central1"
}

variable "artifact_repository_id" {
  description = "Existing Artifact Registry Docker repository id."
  type        = string
  default     = "momo-fraud"
}

variable "deploy_job" {
  description = "Set true after the retraining Docker image has been built and pushed."
  type        = bool
  default     = false
}

variable "container_image" {
  description = "Retraining job container image URI in Artifact Registry."
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "job_name" {
  description = "Cloud Run Job name."
  type        = string
  default     = "momo-fraud-retraining"
}

variable "scheduler_name" {
  description = "Cloud Scheduler job name."
  type        = string
  default     = "momo-fraud-weekly-retraining"
}

variable "schedule" {
  description = "Cron schedule for retraining. Default is every Sunday at midnight."
  type        = string
  default     = "0 0 * * 0"
}

variable "time_zone" {
  description = "Time zone for the scheduler."
  type        = string
  default     = "Africa/Accra"
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
  description = "GCS bucket where MLflow stores run artifacts."
  type        = string
  default     = "momo-fraud-momo-fraud-mlflow-artifacts"
}

variable "prediction_api_url" {
  description = "Live prediction API base URL. train.py calls /reload-model here after a model is promoted."
  type        = string
  default     = "https://momo-fraud-api-7e2lu7f7ta-uc.a.run.app"
}

variable "training_data_bucket_name" {
  description = "Cloud Storage bucket that stores the latest training CSV. Leave null to use a project-based default."
  type        = string
  default     = null
}

variable "training_data_object" {
  description = "Object path inside the training data bucket used by train.py."
  type        = string
  default     = "Pay-sim.csv"
}

variable "job_cpu" {
  description = "Cloud Run Job CPU limit."
  type        = string
  default     = "2"
}

variable "job_memory" {
  description = "Cloud Run Job memory limit."
  type        = string
  default     = "4Gi"
}

variable "job_timeout" {
  description = "Cloud Run Job task timeout."
  type        = string
  default     = "3600s"
}
