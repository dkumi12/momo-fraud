# Prediction API Container

This directory contains the Dockerfile for the MoMo fraud prediction API Cloud
Run service.

The API service is separate from MLflow:

- MLflow tracks training experiments and model artifacts.
- The prediction API receives transactions and returns fraud predictions.

## Expected Source Files

The Dockerfile expects these files in the repository root when the image is
built:

| Path | Purpose |
| --- | --- |
| `app.py` | FastAPI prediction service from `origin/dwilson`. |
| `features.py` | Shared feature engineering helpers. |
| `requirements.txt` | Python dependencies. |
| `templates/` | HTML demo UI. |
| `models/` | Generated model artifacts used by the API at startup. |

The model artifacts are:

- `models/xgboost.pkl`
- `models/caps.json`
- `models/feature_columns.json`
- `models/threshold.json`

If these files are missing, the current API code will fail during startup
because `app.py` loads the model at import time.

## Deploy

The supported deploy entrypoint is:

```powershell
.\scripts\deploy-api.ps1 -ProjectId "momo-fraud"
```

Terraform for this service lives in:

```text
infra/terraform/prediction-api
```
