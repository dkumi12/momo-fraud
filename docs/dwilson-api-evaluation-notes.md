# Notes From `origin/dwilson`

These notes summarize the API and evaluation-gate work currently on
`origin/dwilson` as of commit `3f9e107`.

## Files Added/Updated By `dwilson`

| File | Purpose |
| --- | --- |
| `app.py` | FastAPI prediction service and HTML demo backend. |
| `train.py` | Training pipeline with MLflow logging and evaluation gate. |
| `features.py` | Shared feature engineering helpers used by training. |
| `Dockerfile` | Container image for the prediction API. |
| `requirements.txt` | Runtime/training dependencies including `mlflow==2.14.3`. |
| `templates/index.html` | HTML demo UI for trying transactions. |

## Prediction API

`app.py` exposes these endpoints:

| Endpoint | Purpose |
| --- | --- |
| `GET /` | Serves the HTML demo UI. |
| `GET /health` | Health check. Returns API status and whether the model is loaded. |
| `GET /model-info` | Returns model name, version, stage, run id, and feature list. |
| `POST /predict` | Scores a transaction. Supports JSON for production clients and form data for the demo UI. |
| `POST /reload-model` | Reloads `models/xgboost.pkl` and threshold metadata without restarting the server. |
| `POST /reset` | Clears demo-session velocity history. |

The JSON `/predict` response already matches the contract shape closely:

```json
{
  "transaction_id": "txn_001",
  "prediction": "FRAUD",
  "fraud": 1,
  "probability": 0.9721,
  "threshold": 0.5,
  "risk_level": "high",
  "reason": "Model score crossed the fraud threshold.",
  "signals": {
    "model_flag": true,
    "velocity_flag": false,
    "rule_flag": false
  },
  "model": {
    "name": "xgboost_momo_baseline",
    "version": "v1.0",
    "stage": "Production",
    "run_id": "mlflow-run-id"
  }
}
```

## Request Logger Hook Point

The request logger should be added inside `POST /predict` after prediction is
computed and before returning the response.

Best fields to log from `dwilson`'s response:

- `transaction_id`
- `prediction`
- `fraud`
- `probability`
- `threshold`
- `risk_level`
- `reason`
- `signals.model_flag`
- `signals.velocity_flag`
- `signals.rule_flag`
- `model.name`
- `model.version`
- `model.stage`
- `model.run_id`
- request latency in milliseconds
- status: `success` or `error`

The Firestore collection from our request logger design is:

```text
prediction_requests
```

## Training And Evaluation Gate

`train.py` now logs training runs to the shared MLflow server:

```python
MLFLOW_TRACKING_URI = os.getenv(
    "MLFLOW_TRACKING_URI",
    "https://momo-mlflow-7e2lu7f7ta-uc.a.run.app",
)
MLFLOW_EXPERIMENT = os.getenv("MLFLOW_EXPERIMENT_NAME", "momo-fraud")
MODEL_NAME = "xgboost_momo_baseline"
```

Training flow:

1. Load and clean `Pay-sim.csv`.
2. Split into train, validation, and test sets.
3. Fit preprocessing caps on train only.
4. Apply SMOTE to the training split.
5. Log baseline models to MLflow:
   - `logistic_regression`
   - `random_forest`
6. Train XGBoost production candidate.
7. Log XGBoost params and metrics to MLflow.
8. Run the evaluation gate.
9. Save local serving artifacts into `models/`.

Evaluation gate logic:

- Looks for the latest MLflow run tagged `stage = Production`.
- If none exists, promotes the new XGBoost run by tagging it as Production.
- If a Production run exists, compares:
  - `test_f1`
  - `test_auc`
- Promotes the new model only if:
  - new `test_f1` is higher, or
  - `test_f1` ties and new `test_auc` is higher.
- Removes the old Production tag before tagging the new run.

## Model Artifacts Expected By API

`app.py` loads local artifacts from `models/`:

| Artifact | Purpose |
| --- | --- |
| `models/xgboost.pkl` | Pickled XGBoost model. |
| `models/caps.json` | Winsorization caps used during feature preprocessing. |
| `models/feature_columns.json` | Exact serving feature order. |
| `models/threshold.json` | Fraud threshold, MLflow run id, model version, promotion status. |

## API Dockerfile

`dwilson` added a root `Dockerfile` for the prediction API:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

When we add Terraform for the prediction API, this Dockerfile can be moved or
copied into `deploy/prediction-api/` for consistency with the MLflow container
layout.
