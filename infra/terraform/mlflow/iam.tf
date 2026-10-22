resource "google_storage_bucket_iam_member" "cloud_run_artifact_admin" {
  bucket = google_storage_bucket.mlflow_artifacts.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.cloud_run.email}"
}

resource "google_project_iam_member" "cloud_run_cloudsql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.cloud_run.email}"
}

resource "google_project_iam_member" "cloud_build_storage_viewer" {
  project = var.project_id
  role    = "roles/storage.objectViewer"
  member  = "serviceAccount:${local.cloud_build_runtime_sa}"
}

resource "google_artifact_registry_repository_iam_member" "cloud_build_artifact_writer" {
  location   = google_artifact_registry_repository.docker.location
  repository = google_artifact_registry_repository.docker.name
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${local.cloud_build_runtime_sa}"
}

resource "google_secret_manager_secret_iam_member" "cloud_run_secret_accessor" {
  secret_id = google_secret_manager_secret.db_password.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloud_run.email}"
}

resource "google_cloud_run_v2_service_iam_member" "public_invoker" {
  count = var.deploy_cloud_run && var.allow_unauthenticated ? 1 : 0

  location = google_cloud_run_v2_service.mlflow[0].location
  name     = google_cloud_run_v2_service.mlflow[0].name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
