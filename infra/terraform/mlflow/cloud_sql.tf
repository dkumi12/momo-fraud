resource "google_sql_database_instance" "mlflow" {
  depends_on = [google_project_service.required]

  name             = local.db_instance_name
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier              = var.cloud_sql_tier
    availability_type = var.cloud_sql_availability_type
    disk_size         = var.cloud_sql_disk_size_gb
    disk_type         = "PD_SSD"
    disk_autoresize   = true

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
    }

    ip_configuration {
      ipv4_enabled = var.cloud_sql_ipv4_enabled
    }

    user_labels = local.labels
  }

  deletion_protection = var.deletion_protection
}

resource "google_sql_database" "mlflow" {
  name     = local.db_name
  instance = google_sql_database_instance.mlflow.name
}

resource "google_sql_user" "mlflow" {
  name     = local.db_user
  instance = google_sql_database_instance.mlflow.name
  password = random_password.db_password.result
}
