resource "google_service_account" "api" {
  depends_on = [google_project_service.required]

  account_id   = "momo-fraud-api"
  display_name = "MoMo Fraud Prediction API"
}
