resource "google_firestore_database" "request_logs" {
  depends_on = [google_project_service.required]

  project                     = var.project_id
  name                        = var.database_name
  location_id                 = var.firestore_location
  type                        = "FIRESTORE_NATIVE"
  delete_protection_state     = var.delete_protection_state
  deletion_policy             = "DELETE"
  concurrency_mode            = "OPTIMISTIC"
  app_engine_integration_mode = "DISABLED"
}
