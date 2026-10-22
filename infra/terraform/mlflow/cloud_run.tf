resource "google_cloud_run_v2_service" "mlflow" {
  count = var.deploy_cloud_run ? 1 : 0

  name     = var.cloud_run_service_name
  location = var.region
  labels   = local.labels
  ingress  = var.cloud_run_ingress

  template {
    service_account = google_service_account.cloud_run.email

    scaling {
      min_instance_count = 0
      max_instance_count = var.cloud_run_max_instances
    }

    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [local.cloudsql_connection_name]
      }
    }

    containers {
      image = var.container_image

      ports {
        container_port = 8080
      }

      env {
        name  = "ARTIFACT_ROOT"
        value = local.artifact_root
      }

      env {
        name  = "BACKEND_STORE_URI"
        value = local.backend_store_uri
      }

      resources {
        limits = {
          cpu    = var.cloud_run_cpu
          memory = var.cloud_run_memory
        }
      }

      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }
    }
  }

  depends_on = [
    google_sql_database.mlflow,
    google_sql_user.mlflow,
    google_storage_bucket_iam_member.cloud_run_artifact_admin,
    google_project_iam_member.cloud_run_cloudsql_client
  ]
}
