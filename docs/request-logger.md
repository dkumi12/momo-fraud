# Request Logger Design

The request logger records prediction API activity. It is separate from MLflow:

- MLflow logs training experiments, parameters, metrics, and model artifacts.
- The request logger logs production-style prediction requests and responses.

## Recommended Backend

Use Firestore in Native mode for this project.

Why Firestore:

- Serverless and simple to operate.
- Good fit for JSON request/response logs.
- Easy to query by transaction id, prediction, timestamp, or model version.
- No server to manage for a class/demo project.

## What To Log

Log one document per prediction request in a collection called:

```text
prediction_requests
```

Example document:

```json
{
  "request_id": "req_20260621_0001",
  "transaction_id": "txn_001",
  "created_at": "2026-06-21T12:00:00Z",
  "api_version": "v1",
  "model_name": "xgboost_momo_baseline",
  "model_version": "v1.0",
  "model_stage": "Production",
  "prediction": "FRAUD",
  "fraud": 1,
  "probability": 0.9721,
  "threshold": 0.5,
  "risk_level": "high",
  "latency_ms": 42,
  "status": "success",
  "error": null
}
```

## What Not To Log

Avoid storing sensitive customer data.

Do not log:

- Full customer names.
- Phone numbers.
- Account numbers.
- Raw authentication tokens.
- Any secret keys.

If an identifier is needed, log a safe transaction id or hashed account id.

## API Flow

The prediction API should:

1. Receive the transaction request.
2. Generate a `request_id`.
3. Run model prediction.
4. Return the prediction response to the caller.
5. Write a request log document to Firestore.

For the first version, direct Firestore writes from the API are fine.

For a more production-grade version, the API can publish logs to Pub/Sub and a
separate worker can write them to Firestore. That avoids slowing down prediction
responses if logging has a temporary issue.

## Cloud Resources

The Terraform stack in `infra/terraform/request-logger` provisions:

- Firestore Native database.
- Service account for the API/request logger.
- IAM permission to write request logs.

When the prediction API Cloud Run service is added, it should run with this
service account or receive the same Firestore IAM permission.
