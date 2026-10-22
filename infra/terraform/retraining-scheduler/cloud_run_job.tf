resource "google_cloud_run_v2_job" "retraining" {
  count = var.deploy_job ? 1 : 0

  name     = var.job_name
  location = var.region
  labels   = local.labels

  template {
    template {
      service_account = google_service_account.training_job.email
      timeout         = var.job_timeout
      max_retries     = 0

      containers {
        image = var.container_image

        env {
          name  = "MLFLOW_TRACKING_URI"
          value = var.mlflow_tracking_uri
        }

        env {
          name  = "MLFLOW_EXPERIMENT_NAME"
          value = var.mlflow_experiment_name
        }

        env {
          name  = "TRAINING_DATA_URI"
          value = local.training_data_uri
        }

        env {
          name  = "PREDICTION_API_URL"
          value = var.prediction_api_url
        }

        env {
          name  = "PYTHONIOENCODING"
          value = "utf-8"
        }

        resources {
          limits = {
            cpu    = var.job_cpu
            memory = var.job_memory
          }
        }
      }
    }
  }

  depends_on = [
    google_artifact_registry_repository_iam_member.training_job_artifact_reader,
    google_storage_bucket_iam_member.training_job_data_reader
  ]
}
