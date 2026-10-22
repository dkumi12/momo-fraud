locals {
  labels = {
    app     = "momo-fraud"
    service = "mlflow"
  }

  bucket_name              = coalesce(var.artifact_bucket_name, "${var.project_id}-momo-fraud-mlflow-artifacts")
  service_account_id       = "momo-mlflow-runner"
  db_instance_name         = "momo-mlflow-postgres"
  db_name                  = "mlflow"
  db_user                  = "mlflow"
  db_password_secret_name  = "momo-mlflow-db-password"
  cloud_build_runtime_sa   = "${data.google_project.current.number}-compute@developer.gserviceaccount.com"
  cloudsql_connection_name = google_sql_database_instance.mlflow.connection_name
  artifact_root            = "gs://${google_storage_bucket.mlflow_artifacts.name}"
  backend_store_uri        = "postgresql+psycopg2://${local.db_user}:${urlencode(random_password.db_password.result)}@/${local.db_name}?host=/cloudsql/${local.cloudsql_connection_name}"
}
