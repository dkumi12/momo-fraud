# Terraform: Request Logger

This stack provisions the backend used to log prediction API requests.

It creates:

- Firestore Native database.
- Service account for the prediction API/request logger.
- IAM permission for that service account to write Firestore documents.

## Why This Is Separate From MLflow

MLflow tracks model training:

- experiments
- parameters
- metrics
- model artifacts

The request logger tracks prediction API usage:

- request id
- transaction id
- prediction result
- probability
- model version used
- latency
- errors

## Deploy

From this directory:

```powershell
Copy-Item terraform.tfvars.example terraform.tfvars
terraform init
terraform apply -var-file="terraform.tfvars"
```

If Firestore already exists in the project, Terraform may ask you to import it
instead of creating it. Firestore allows only one default database per project.

## API Integration

When the prediction API Cloud Run service is created, run it with the service
account output by this stack:

```powershell
terraform output api_logger_service_account
```

The API should write one document per request to:

```text
prediction_requests
```

See `docs/request-logger.md` for the recommended log schema.
