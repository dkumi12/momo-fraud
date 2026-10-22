resource "google_project_iam_member" "api_logger_datastore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.api_logger.email}"
}
