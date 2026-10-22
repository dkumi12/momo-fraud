data "google_artifact_registry_repository" "docker" {
  depends_on = [google_project_service.required]

  location      = var.region
  repository_id = var.artifact_repository_id
}
