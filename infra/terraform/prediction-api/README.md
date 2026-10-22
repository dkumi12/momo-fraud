# Terraform: Prediction API on Cloud Run

This stack provisions the Cloud Run service for the fraud prediction API.

It creates:

- Prediction API Cloud Run service.
- Service account for the API.
- IAM permission for Firestore request logging.
- IAM permission to read the API image from Artifact Registry.

It reuses the existing Artifact Registry repository created during the MLflow
setup.

## Important Runtime Requirement

The current API implementation from `origin/dwilson` loads model artifacts at
startup from:

```text
models/xgboost.pkl
models/caps.json
models/feature_columns.json
models/threshold.json
```

Those files must exist before building the API image. Otherwise Cloud Run will
deploy the container but the app will fail during startup.

## Deploy

From the repository root:

```powershell
Copy-Item infra\terraform\prediction-api\terraform.tfvars.example infra\terraform\prediction-api\terraform.tfvars
.\scripts\deploy-api.ps1 -ProjectId "momo-fraud"
```

The script:

1. Runs Terraform once to create IAM/service account setup.
2. Builds and pushes the API image.
3. Runs Terraform again to deploy Cloud Run using that image.
4. Prints the service URL and health check URL.
