output "retraining_image_uri" {
  description = "Recommended image URI for the retraining job container."
  value       = local.image_uri
}

output "retraining_job_name" {
  description = "Cloud Run Job name."
  value       = var.job_name
}

output "scheduler_name" {
  description = "Cloud Scheduler job name."
  value       = var.deploy_job ? google_cloud_scheduler_job.weekly_retraining[0].name : null
}

output "scheduler_schedule" {
  description = "Retraining cadence."
  value       = "${var.schedule} (${var.time_zone})"
}

output "training_data_uri" {
  description = "Cloud Storage URI that train.py downloads when the job runs."
  value       = local.training_data_uri
}

output "manual_run_command" {
  description = "Command to manually run the retraining job."
  value       = "gcloud run jobs execute ${var.job_name} --region ${var.region} --project ${var.project_id}"
}
