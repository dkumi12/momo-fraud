resource "google_project_service" "required" {
  for_each = toset([
    "datastore.googleapis.com",
    "firestore.googleapis.com",
    "iam.googleapis.com"
  ])

  service            = each.key
  disable_on_destroy = false
}
