# Terraform: MLflow on Cloud Run

This Terraform stack provisions the durable pieces for MLflow:

- Artifact Registry Docker repository.
- Cloud Storage bucket for MLflow artifacts.
- Cloud SQL PostgreSQL instance for MLflow metrics/params/run metadata.
- Secret Manager password for the database user.
- Cloud Run service account and IAM.
- Cloud Run service for the MLflow tracking UI/server.

Cloud Run itself remains stateless. Metrics and params live in Cloud SQL, while
models and generated artifacts live in Cloud Storage.

## File Layout

Each resource group is separated so the infrastructure is easy to review:

| File | Purpose |
| --- | --- |
| `providers.tf` | Terraform and provider configuration. |
| `apis.tf` | Required GCP APIs. |
| `locals.tf` | Shared names, labels, and derived connection strings. |
| `artifact_registry.tf` | Docker repository for MLflow images. |
| `storage.tf` | Cloud Storage bucket for MLflow artifacts. |
| `service_account.tf` | Cloud Run service account. |
| `iam.tf` | IAM bindings for Storage, Cloud SQL, Secret Manager, Cloud Build image publishing, and optional public Cloud Run access. |
| `secrets.tf` | Generated database password and Secret Manager storage. |
| `cloud_sql.tf` | Cloud SQL PostgreSQL instance, database, and user. |
| `cloud_run.tf` | MLflow Cloud Run service. |
| `variables.tf` | Input variables. |
| `outputs.tf` | Useful deployment outputs. |

## One-Command Deploy

From the repository root:

```powershell
Copy-Item infra\terraform\mlflow\terraform.tfvars.example infra\terraform\mlflow\terraform.tfvars
notepad infra\terraform\mlflow\terraform.tfvars
.\scripts\deploy-mlflow.ps1 -ProjectId "your-gcp-project-id"
```

The script does the calm version of the workflow:

1. Runs `terraform init`.
2. Applies Terraform with `deploy_cloud_run=false` to create the bucket, database,
   service account, and Artifact Registry repository.
3. Builds and pushes the MLflow Docker image.
4. Applies Terraform again with `deploy_cloud_run=true` and the pushed image URI.
5. Prints the MLflow tracking URL.

## Manual Terraform

```powershell
cd infra\terraform\mlflow
terraform init
terraform apply -var-file="terraform.tfvars" -var="deploy_cloud_run=false"

$image = terraform output -raw mlflow_image_uri
gcloud builds submit ..\..\..\deploy\mlflow-cloud-run --tag $image

terraform apply -var-file="terraform.tfvars" -var="deploy_cloud_run=true" -var="container_image=$image"
terraform output cloud_run_service_url
```

## Notes

- `terraform.tfvars` is ignored by Git so project ids and settings do not leak.
- The generated database password is stored in Terraform state and Secret
  Manager. Keep your Terraform state private.
- `deletion_protection` defaults to `true` for Cloud SQL. Set it to `false` only
  when you intentionally want to destroy the database.
- `cloud_sql_ipv4_enabled` defaults to `true` because Cloud SQL requires public
  IP, private IP, or PSC connectivity. Cloud Run still uses the Cloud SQL
  connector socket; do not set this to `false` unless private IP or PSC has been
  added.
- `cloud_run_ingress` controls whether the direct `https://*.run.app` URL is
  reachable. Keep `INGRESS_TRAFFIC_ALL` for simple access. Authentication is
  controlled separately by `allow_unauthenticated`.
- Cloud Build uses the project's compute default service account in this setup.
  Terraform grants it read access to the Cloud Build staging object and write
  access to the Artifact Registry repository so `gcloud builds submit` can push
  the MLflow image.
- Public MLflow access is off by default. Keep `allow_unauthenticated=false` for
  real work and use authenticated access.
