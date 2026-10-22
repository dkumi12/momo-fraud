output "firestore_database" {
  description = "Firestore database used for prediction request logs."
  value       = google_firestore_database.request_logs.name
}

output "firestore_location" {
  description = "Firestore database location."
  value       = google_firestore_database.request_logs.location_id
}

output "request_log_collection" {
  description = "Recommended collection name for API request logs."
  value       = "prediction_requests"
}

output "api_logger_service_account" {
  description = "Service account to use for the prediction API when writing request logs."
  value       = google_service_account.api_logger.email
}
