# MLflow Tracking Server on Cloud Run

This directory contains only the MLflow tracking server container image.

The supported deployment path is Terraform plus the wrapper script:

```powershell
.\scripts\deploy-mlflow.ps1 -ProjectId "momo-fraud"
```

That script provisions infrastructure, builds this image, pushes it to Artifact
Registry, and deploys Cloud Run.

## Runtime Architecture

MLflow runs on Cloud Run with:

- Cloud SQL for experiment/run metadata.
- Cloud Storage for model artifacts.
- Artifact Registry for the container image.

Cloud Run containers are ephemeral, so do not use local SQLite or local artifact
paths for the shared tracking server.

## Files

| File | Purpose |
| --- | --- |
| `Dockerfile` | Builds the MLflow server container used by Cloud Run. |

Infrastructure lives in `infra/terraform/mlflow`. The one supported deploy
entrypoint is `scripts/deploy-mlflow.ps1`.

## Training Configuration

Training jobs should point to the deployed Cloud Run service URL:

```powershell
$env:MLFLOW_TRACKING_URI="https://momo-mlflow-7e2lu7f7ta-uc.a.run.app"
$env:MLFLOW_EXPERIMENT_NAME="momo-fraud"
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

- `allow_unauthenticated = true` is convenient for class/demo handoff.
- For private access, set `allow_unauthenticated = false` in Terraform and grant
  Cloud Run invoker permissions to approved users/jobs.
- Do not store credentials in `.env` or committed files.
- Restrict Cloud SQL and bucket permissions to the Cloud Run service account.
