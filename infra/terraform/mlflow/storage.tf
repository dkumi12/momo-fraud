resource "google_storage_bucket" "mlflow_artifacts" {
  depends_on = [google_project_service.required]

  name                        = local.bucket_name
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = var.force_destroy_bucket
  labels                      = local.labels

  versioning {
    enabled = true
  }
}
