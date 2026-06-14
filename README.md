# MoMo Fraud Detection

This repo now has two connected tracks:

1. ML/model work: train the fraud model and log runs to MLflow.
2. Cloud/API work: define the prediction API contract and host MLflow on Cloud Run.

## Current Cloud Setup

MLflow is deployed on Cloud Run:

```text
https://momo-mlflow-7e2lu7f7ta-uc.a.run.app
```

The ML team should use:

```powershell
$env:MLFLOW_TRACKING_URI="https://momo-mlflow-7e2lu7f7ta-uc.a.run.app"
$env:MLFLOW_EXPERIMENT_NAME="momo-fraud"
```

MLflow data is durable:

- Metrics, parameters, and run metadata go to Cloud SQL PostgreSQL.
- Model artifacts go to Cloud Storage.
- The MLflow container image is stored in Artifact Registry.

## Folder Structure

| Path | Purpose |
| --- | --- |
| `API_CONTRACT.md` | Agreement between cloud/API and ML teammates for prediction requests and responses. |
| `api/` | Early FastAPI prediction API scaffold. |
| `deploy/mlflow-cloud-run/` | MLflow server container only. Contains the Dockerfile Cloud Run uses. |
| `infra/terraform/mlflow/` | Terraform resources for MLflow infrastructure. Each resource group has its own `.tf` file. |
| `scripts/deploy-mlflow.ps1` | One-command deployment wrapper for Terraform plus image build. |
| `src/` | ML source code area. |
| `notebooks/` | Notebook area for EDA/training experiments. |

## Why `deploy/mlflow-cloud-run/` Exists

Terraform can create cloud resources, but Cloud Run also needs a Docker image.
The `deploy/mlflow-cloud-run/` folder contains the Dockerfile for that image.

So the responsibilities are:

- `deploy/mlflow-cloud-run/Dockerfile`: says how to run MLflow inside a container.
- `infra/terraform/mlflow/`: says which GCP resources should exist.
- `scripts/deploy-mlflow.ps1`: runs Terraform, builds the Docker image, pushes it,
  and deploys Cloud Run.

That folder is necessary unless we stop hosting MLflow ourselves and move to a
fully managed alternative.

## Main Deploy Command

From the repo root:

```powershell
.\scripts\deploy-mlflow.ps1 -ProjectId "momo-fraud"
```

This is the only supported deploy command for MLflow.
