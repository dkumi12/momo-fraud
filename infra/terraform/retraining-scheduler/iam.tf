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

resource "google_artifact_registry_repository_iam_member" "training_job_artifact_reader" {
  location   = data.google_artifact_registry_repository.docker.location
  repository = var.artifact_repository_id
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${google_service_account.training_job.email}"
}

resource "google_storage_bucket_iam_member" "training_job_data_reader" {
  bucket = google_storage_bucket.training_data.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.training_job.email}"
}

resource "google_storage_bucket_iam_member" "training_job_mlflow_artifact_writer" {
  bucket = var.mlflow_artifact_bucket_name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.training_job.email}"
}

resource "google_project_iam_member" "scheduler_run_developer" {
  project = var.project_id
  role    = "roles/run.developer"
  member  = "serviceAccount:${google_service_account.scheduler.email}"
}

resource "google_service_account_iam_member" "scheduler_uses_training_job_sa" {
  service_account_id = google_service_account.training_job.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.scheduler.email}"
}
