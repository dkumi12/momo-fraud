resource "google_cloud_run_v2_service" "api" {
  count = var.deploy_cloud_run ? 1 : 0

  name     = var.cloud_run_service_name
  location = var.region
  labels   = local.labels
  ingress  = var.cloud_run_ingress

  template {
    service_account = google_service_account.api.email

    scaling {
      min_instance_count = 0
      max_instance_count = var.cloud_run_max_instances
    }

    containers {
      image = var.container_image

      ports {
        container_port = 8080
      }

      env {
        name  = "MLFLOW_TRACKING_URI"
        value = var.mlflow_tracking_uri
      }

      env {
        name  = "MLFLOW_EXPERIMENT_NAME"
        value = var.mlflow_experiment_name
      }

      env {
        name  = "REQUEST_LOG_COLLECTION"
        value = var.request_log_collection
      }

      resources {
        limits = {
          cpu    = var.cloud_run_cpu
          memory = var.cloud_run_memory
        }
      }
    }
  }

  depends_on = [
    google_project_iam_member.api_datastore_user,
    google_artifact_registry_repository_iam_member.cloud_run_artifact_reader
  ]
}
