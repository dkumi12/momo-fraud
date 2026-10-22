resource "random_password" "db_password" {
  length           = 32
  special          = true
  override_special = "_-"
}

resource "google_secret_manager_secret" "db_password" {
  depends_on = [google_project_service.required]

  secret_id = local.db_password_secret_name
  labels    = local.labels

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "db_password" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = random_password.db_password.result
}
