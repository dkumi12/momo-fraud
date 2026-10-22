resource "google_project_iam_member" "api_datastore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.api.email}"
}

resource "google_storage_bucket_iam_member" "api_mlflow_artifact_reader" {
  bucket = var.mlflow_artifact_bucket_name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.api.email}"
}

resource "google_artifact_registry_repository_iam_member" "cloud_run_artifact_reader" {
  location   = data.google_artifact_registry_repository.docker.location
  repository = var.artifact_repository_id
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${google_service_account.api.email}"
}

resource "google_project_iam_member" "cloud_build_storage_viewer" {
  project = var.project_id
  role    = "roles/storage.objectViewer"
  member  = "serviceAccount:${local.cloud_build_runtime_sa}"
}

resource "google_artifact_registry_repository_iam_member" "cloud_build_artifact_writer" {
  location   = data.google_artifact_registry_repository.docker.location
  repository = var.artifact_repository_id
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${local.cloud_build_runtime_sa}"
}

resource "google_cloud_run_v2_service_iam_member" "public_invoker" {
  count = var.deploy_cloud_run && var.allow_unauthenticated ? 1 : 0

  location = google_cloud_run_v2_service.api[0].location
  name     = google_cloud_run_v2_service.api[0].name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
