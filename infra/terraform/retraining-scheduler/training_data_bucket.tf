resource "google_storage_bucket" "training_data" {
  name                        = coalesce(var.training_data_bucket_name, "${var.project_id}-momo-fraud-training-data")
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = false
  labels                      = local.labels
}
