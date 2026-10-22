# MoMo Fraud Detection API Contract

This contract defines the interface between the ML service and cloud/application
clients. It is based on the current service work from `origin/dwilson` and keeps
the serving API stable while the model and tracking infrastructure evolve.

## Simple Summary for the ML Partner

The API has one main job: receive a mobile money transaction and return whether
the transaction looks fraudulent.

The most important endpoint is:

```text
POST /predict
```

Your model-serving code should accept a transaction like this:

```json
{
  "transaction_id": "txn_001",
  "type": "TRANSFER",
  "amount": 4500.0,
  "oldbalanceOrg": 12500.0,
  "newbalanceOrig": 8000.0,
  "oldbalanceDest": 8500.0,
  "newbalanceDest": 13000.0
}
```

And return a result like this:

```json
{
  "prediction": "FRAUD",
  "fraud": 1,
  "probability": 0.9721,
  "reason": "Model score crossed the fraud threshold."
}
```

In plain English:

- `prediction` is the human-readable answer: `FRAUD` or `LEGITIMATE`.
- `fraud` is the machine-readable answer: `1` for fraud, `0` for legitimate.
- `probability` is the model confidence between `0` and `1`.
- `reason` explains why the transaction was flagged or cleared.

The other endpoints are support endpoints:

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Cloud Run uses this to confirm the API is alive. |
| `GET /model-info` | Shows which model/version is currently loaded. |
| `POST /reload-model` | Reloads the production model without rebuilding the API container. |

MLflow is separate from the prediction API. Use MLflow to log training runs,
metrics, parameters, and model artifacts. Use this API contract when exposing the
trained model for predictions.

## Versioning

- Contract version: `v1`
- Base path: `/`
- Transport: HTTPS in deployed environments
- Request body format: JSON for production integrations
- Response body format: JSON
- Timestamps: ISO 8601 UTC when present

## Health Check

### `GET /health`

Used by Cloud Run and uptime checks.

Response `200`:

```json
{
  "status": "ok",
  "service": "momo-fraud-api",
  "model_loaded": true
}
```

## Prediction

### `POST /predict`

Scores one mobile money transaction and returns the model decision plus any
rule/velocity signal.

Request:

```json
{
  "transaction_id": "txn_20260614_0001",
  "session_id": "demo-session-1",
  "step": 200,
  "type": "TRANSFER",
  "amount": 4500.0,
  "oldbalanceOrg": 12500.0,
  "newbalanceOrig": 8000.0,
  "oldbalanceDest": 8500.0,
  "newbalanceDest": 13000.0,
  "recipient_id": "kwame",
  "is_dest_merchant": false
}
```

Field requirements:

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `transaction_id` | string | yes | Caller-generated idempotency key. |
| `session_id` | string | no | Used for velocity/smurfing checks. Defaults to `default`. |
| `step` | integer | yes | PaySim-style simulation step or transaction time bucket. |
| `type` | string | yes | One of `PAYMENT`, `TRANSFER`, `CASH_OUT`, `CASH_IN`, `DEBIT`. |
| `amount` | number | yes | Must be greater than `0`. |
| `oldbalanceOrg` | number | yes | Sender balance before transaction. |
| `newbalanceOrig` | number | yes | Sender balance after transaction. |
| `oldbalanceDest` | number | yes | Recipient balance before transaction. |
| `newbalanceDest` | number | yes | Recipient balance after transaction. |
| `recipient_id` | string | no | Used for velocity and destination rules when available. |
| `is_dest_merchant` | boolean | no | Defaults to `false` when omitted. |

Response `200`:

```json
{
  "transaction_id": "txn_20260614_0001",
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

Validation error `422`:

```json
{
  "error": "validation_error",
  "message": "amount must be greater than 0",
  "fields": {
    "amount": "must be greater than 0"
  }
}
```

Runtime error `500`:

```json
{
  "error": "prediction_error",
  "message": "Unable to score transaction"
}
```

## Model Info

### `GET /model-info`

Returns the model currently loaded by the API.

Response `200`:

```json
{
  "model_name": "xgboost_momo_baseline",
  "version": "v1.0",
  "stage": "Production",
  "run_id": "mlflow-run-id",
  "artifact_uri": "gs://momo-fraud-mlflow-artifacts/...",
  "features": [
    "step",
    "type",
    "amount",
    "oldbalanceOrg",
    "newbalanceOrig",
    "oldbalanceDest",
    "newbalanceDest",
    "isDestMerchant",
    "errorBalanceOrig",
    "errorBalanceDest"
  ]
}
```

## Reload Model

### `POST /reload-model`

Reloads the model artifact without rebuilding the container. This endpoint should
be protected in production with IAM, an internal ingress policy, or a signed
scheduler request.

Request:

```json
{
  "model_name": "xgboost_momo_baseline",
  "stage": "Production"
}
```

Response `200`:

```json
{
  "status": "reloaded",
  "model_name": "xgboost_momo_baseline",
  "version": "v1.0",
  "stage": "Production"
}
```

## Compatibility Note

The current demo service on `origin/dwilson` accepts form fields for `/predict`
because it serves an HTML demo. Production clients should use the JSON contract
above. If the demo UI remains, the API can support both form and JSON input while
returning the same response shape.
