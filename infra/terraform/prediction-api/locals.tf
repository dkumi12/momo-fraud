locals {
  labels = {
    app     = "momo-fraud"
    service = "prediction-api"
  }

  image_uri              = "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_repository_id}/prediction-api:latest"
  cloud_build_runtime_sa = "${data.google_project.current.number}-compute@developer.gserviceaccount.com"
}
