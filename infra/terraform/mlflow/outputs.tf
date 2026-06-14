output "artifact_bucket" {
  description = "GCS bucket used for durable MLflow artifacts."
  value       = google_storage_bucket.mlflow_artifacts.url
}

output "artifact_repository" {
  description = "Artifact Registry repository."
  value       = google_artifact_registry_repository.docker.id
}

output "mlflow_image_uri" {
  description = "Recommended image URI for the MLflow tracking server container."
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_repository_id}/mlflow-tracking:latest"
}

output "cloud_sql_connection_name" {
  description = "Cloud SQL connection name used by Cloud Run."
  value       = google_sql_database_instance.mlflow.connection_name
}

output "cloud_run_service_url" {
  description = "MLflow tracking URL after deploy_cloud_run is true."
  value       = var.deploy_cloud_run ? google_cloud_run_v2_service.mlflow[0].uri : null
}

output "tracking_env" {
  description = "Environment variable to use in training after Cloud Run is deployed."
  value       = var.deploy_cloud_run ? "MLFLOW_TRACKING_URI=${google_cloud_run_v2_service.mlflow[0].uri}" : "Set deploy_cloud_run=true after building the image."
}
