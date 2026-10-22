locals {
  labels = {
    app     = "momo-fraud"
    service = "retraining"
  }

  image_uri              = "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_repository_id}/retraining-job:latest"
  cloud_build_runtime_sa = "${data.google_project.current.number}-compute@developer.gserviceaccount.com"
  run_job_uri            = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/${var.job_name}:run"
  training_data_uri      = "gs://${google_storage_bucket.training_data.name}/${var.training_data_object}"
}
