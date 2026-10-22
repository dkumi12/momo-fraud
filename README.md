# MoMo Fraud Detection

An end-to-end fraud-detection prototype for mobile-money transactions. The project trains and evaluates baseline classifiers, promotes a production candidate through an MLflow evaluation gate, and serves predictions through a FastAPI application designed for Cloud Run.

> **Portfolio scope:** This is a technical prototype built with PaySim-style transaction data. It is not a production financial-decisioning system and must not be used as the sole basis for blocking or approving real customer transactions.

## Highlights

- **Imbalance-aware ML pipeline:** logistic regression, random forest, and XGBoost baselines with SMOTE applied only to the training split.
- **Reproducible promotion gate:** the candidate model is compared against the current production run by test F1, then test AUC when F1 is tied.
- **Serving layer:** FastAPI prediction, health, model-information, and reload endpoints, plus a browser-based demo flow.
- **Operational foundation:** MLflow tracking, Cloud Run deployment assets, Terraform infrastructure, Firestore request logging, and scheduled retraining scaffolding.
- **Guardrails:** thresholding is tuned on the validation split; prediction responses include model, velocity, and rule signals rather than presenting a score as certainty.

## Architecture

```text
PaySim-style data -> feature engineering -> SMOTE on training split -> model evaluation
       |                                                           |
       +-------------------------------> MLflow <------------------+
                                                                  |
FastAPI demo / JSON client -> prediction API -> production model + velocity/rule checks
                                                                  |
                                                     structured request logging
```

## Quick Start

1. Create and activate a Python virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Start the demo/API with `uvicorn app:app --reload`.
4. Open `http://127.0.0.1:8000` for the demo interface, or read [`API_CONTRACT.md`](API_CONTRACT.md) for the JSON API.

The checked-in model artifacts in `models/` support the local demo. Training requires a PaySim-compatible CSV with the expected transaction fields. For remote training data, set `TRAINING_DATA_URI` to a `gs://` object; then run `python train.py` after configuring MLflow access.

## Responsible Use and Limitations

- PaySim-style data is simulated and does not establish performance on a real mobile-money population.
- A fraud score is a triage signal; human review, investigation controls, and an appeal process are required before adverse customer action.
- Thresholds, class balance, drift, false-positive impact, privacy controls, and operational latency must be monitored before any production use.
- Do not commit credentials, Terraform state, raw customer data, or proprietary transaction records. See [`model_card.md`](model_card.md) and [`known-issues.md`](known-issues.md).

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
| `deploy/prediction-api/` | Prediction API container image definition. |
| `deploy/training-job/` | Retraining Cloud Run Job container image definition. |
| `infra/terraform/mlflow/` | Terraform resources for MLflow infrastructure. Each resource group has its own `.tf` file. |
| `infra/terraform/prediction-api/` | Terraform resources for the prediction API Cloud Run service. |
| `infra/terraform/request-logger/` | Terraform resources for Firestore request logging. |
| `infra/terraform/retraining-scheduler/` | Terraform resources for weekly automated retraining. |
| `scripts/deploy-mlflow.ps1` | One-command deployment wrapper for Terraform plus image build. |
| `scripts/deploy-api.ps1` | One-command deployment wrapper for the prediction API. |
| `scripts/deploy-retraining-scheduler.ps1` | One-command deployment wrapper for the retraining scheduler. |
| `docs/request-logger.md` | Request logger design and log schema. |
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
