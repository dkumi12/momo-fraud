variable "project_id" {
  description = "GCP project id."
  type        = string
}

variable "region" {
  description = "Default GCP region."
  type        = string
  default     = "us-central1"
}

variable "firestore_location" {
  description = "Firestore database location."
  type        = string
  default     = "us-central1"
}

variable "database_name" {
  description = "Firestore database name. Use (default) for the default database."
  type        = string
  default     = "(default)"
}

variable "api_logger_service_account_id" {
  description = "Service account id for the prediction API/request logger."
  type        = string
  default     = "momo-api-request-logger"
}

variable "delete_protection_state" {
  description = "Firestore delete protection. Use DELETE_PROTECTION_ENABLED for real environments."
  type        = string
  default     = "DELETE_PROTECTION_ENABLED"
}
