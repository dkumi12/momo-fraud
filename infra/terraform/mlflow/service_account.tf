resource "google_service_account" "cloud_run" {
  depends_on = [google_project_service.required]

  account_id   = local.service_account_id
  display_name = "MoMo MLflow Cloud Run"
}
