resource "google_service_account" "api_logger" {
  depends_on = [google_project_service.required]

  account_id   = var.api_logger_service_account_id
  display_name = "MoMo Fraud API Request Logger"
}
