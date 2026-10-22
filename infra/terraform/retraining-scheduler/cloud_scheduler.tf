resource "google_cloud_scheduler_job" "weekly_retraining" {
  count = var.deploy_job ? 1 : 0

  name        = var.scheduler_name
  description = "Runs the MoMo fraud retraining Cloud Run Job on schedule."
  region      = var.region
  schedule    = var.schedule
  time_zone   = var.time_zone

  http_target {
    http_method = "POST"
    uri         = local.run_job_uri

    oauth_token {
      service_account_email = google_service_account.scheduler.email
      scope                 = "https://www.googleapis.com/auth/cloud-platform"
    }
  }

  depends_on = [
    google_cloud_run_v2_job.retraining,
    google_project_iam_member.scheduler_run_developer,
    google_service_account_iam_member.scheduler_uses_training_job_sa
  ]
}
