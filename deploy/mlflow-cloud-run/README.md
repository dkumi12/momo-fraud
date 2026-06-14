# MLflow Tracking Server on Cloud Run

This setup runs MLflow Tracking on Cloud Run with:

- Cloud SQL for experiment/run metadata.
- Cloud Storage for model artifacts.
- Artifact Registry for the container image.

Cloud Run containers are ephemeral, so do not use local SQLite or local artifact
paths for the shared tracking server.

## Required GCP Resources

Set these names for your project:

```bash
PROJECT_ID="your-gcp-project"
REGION="us-central1"
SERVICE_NAME="momo-mlflow"
ARTIFACT_REPO="momo-fraud"
BUCKET="gs://momo-fraud-mlflow-artifacts"
INSTANCE_CONNECTION_NAME="project:region:instance"
DB_NAME="mlflow"
DB_USER="mlflow"
DB_PASSWORD_SECRET="mlflow-db-password"
```

Create the storage bucket:

```bash
gcloud storage buckets create "$BUCKET" --location="$REGION"
```

Create a PostgreSQL Cloud SQL instance and database:

```bash
gcloud sql instances create momo-mlflow-postgres \
  --database-version=POSTGRES_15 \
  --cpu=1 \
  --memory=4GB \
  --region="$REGION"

gcloud sql databases create "$DB_NAME" --instance=momo-mlflow-postgres
gcloud sql users create "$DB_USER" --instance=momo-mlflow-postgres --password="replace-me"
```

Store the database password in Secret Manager:

```bash
printf "replace-me" | gcloud secrets create "$DB_PASSWORD_SECRET" --data-file=-
```

## Backend Store URI

For Cloud SQL over the Unix socket mounted by Cloud Run:

```bash
BACKEND_STORE_URI="postgresql+psycopg2://mlflow:DB_PASSWORD@/mlflow?host=/cloudsql/project:region:instance"
ARTIFACT_ROOT="gs://momo-fraud-mlflow-artifacts"
```

Prefer passing `BACKEND_STORE_URI` from CI/CD or a local deploy command. Avoid
committing real passwords.

## Build and Deploy

From the repository root:

```bash
gcloud artifacts repositories create "$ARTIFACT_REPO" \
  --repository-format=docker \
  --location="$REGION"

IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/$ARTIFACT_REPO/mlflow-tracking:latest"

gcloud builds submit deploy/mlflow-cloud-run --tag "$IMAGE"

gcloud run deploy "$SERVICE_NAME" \
  --image="$IMAGE" \
  --region="$REGION" \
  --port=8080 \
  --add-cloudsql-instances="$INSTANCE_CONNECTION_NAME" \
  --set-env-vars="ARTIFACT_ROOT=$ARTIFACT_ROOT,BACKEND_STORE_URI=$BACKEND_STORE_URI" \
  --no-allow-unauthenticated
```

Grant the Cloud Run service account access to the artifact bucket and the
database secret if you externalize the password through Secret Manager.

## Training Configuration

Training jobs should point to the Cloud Run service URL:

```bash
export MLFLOW_TRACKING_URI="https://SERVICE_URL"
export MLFLOW_EXPERIMENT_NAME="momo-fraud"
```

Then log parameters, metrics, and model artifacts from `train.py`:

```python
import mlflow

mlflow.set_experiment("momo-fraud")
with mlflow.start_run():
    mlflow.log_param("model_type", "xgboost")
    mlflow.log_metric("f1", f1)
    mlflow.sklearn.log_model(model, "model")
```

## Security Notes

- Keep MLflow private by default with `--no-allow-unauthenticated`.
- Use IAM-authenticated callers for training jobs and admins.
- Do not store credentials in `.env` or committed files.
- Restrict Cloud SQL and bucket permissions to the Cloud Run service account.
