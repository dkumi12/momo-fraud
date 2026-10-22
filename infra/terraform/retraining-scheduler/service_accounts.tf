resource "google_service_account" "training_job" {
  depends_on = [google_project_service.required]

  account_id   = "momo-training-job"
  display_name = "MoMo Fraud Retraining Job"
}

resource "google_service_account" "scheduler" {
  depends_on = [google_project_service.required]

  account_id   = "momo-retraining-scheduler"
  display_name = "MoMo Fraud Retraining Scheduler"
}
