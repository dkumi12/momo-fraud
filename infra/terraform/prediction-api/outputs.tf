output "prediction_api_image_uri" {
  description = "Recommended image URI for the prediction API container."
  value       = local.image_uri
}

output "prediction_api_service_url" {
  description = "Prediction API URL after deploy_cloud_run is true."
  value       = var.deploy_cloud_run ? google_cloud_run_v2_service.api[0].uri : null
}

output "prediction_api_service_account" {
  description = "Cloud Run service account used by the prediction API."
  value       = google_service_account.api.email
}

output "health_check_url" {
  description = "Health endpoint after deploy_cloud_run is true."
  value       = var.deploy_cloud_run ? "${google_cloud_run_v2_service.api[0].uri}/health" : null
}
