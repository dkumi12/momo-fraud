import os
import time
import uuid
from typing import Any

from google.cloud import firestore


REQUEST_LOG_COLLECTION = os.getenv("REQUEST_LOG_COLLECTION", "prediction_requests")

_client: firestore.Client | None = None


def _firestore_client() -> firestore.Client:
    global _client
    if _client is None:
        _client = firestore.Client()
    return _client


def _safe_request_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not payload:
        return {}

    allowed_fields = {
        "transaction_id",
        "session_id",
        "step",
        "type",
        "amount",
        "oldbalanceOrg",
        "newbalanceOrig",
        "oldbalanceDest",
        "newbalanceDest",
        "recipient_id",
        "is_dest_merchant",
    }
    return {key: payload.get(key) for key in allowed_fields if key in payload}


def log_prediction_request(
    *,
    request_payload: dict[str, Any] | None,
    response_payload: dict[str, Any],
    latency_ms: int,
    status: str,
    source: str,
    error: str | None = None,
) -> str | None:
    """
    Write one prediction request/response log to Firestore.

    Logging is best-effort: Firestore issues are printed but do not block the
    prediction API response.
    """
    try:
        request_id = str(uuid.uuid4())
        model = response_payload.get("model", {}) if isinstance(response_payload, dict) else {}
        signals = response_payload.get("signals", {}) if isinstance(response_payload, dict) else {}

        document = {
            "request_id": request_id,
            "created_at": firestore.SERVER_TIMESTAMP,
            "source": source,
            "status": status,
            "error": error,
            "latency_ms": latency_ms,
            "request": _safe_request_payload(request_payload),
            "transaction_id": response_payload.get("transaction_id") or (request_payload or {}).get("transaction_id"),
            "prediction": response_payload.get("prediction"),
            "fraud": response_payload.get("fraud"),
            "probability": response_payload.get("probability"),
            "threshold": response_payload.get("threshold"),
            "risk_level": response_payload.get("risk_level"),
            "reason": response_payload.get("reason"),
            "signals": {
                "model_flag": signals.get("model_flag"),
                "velocity_flag": signals.get("velocity_flag"),
                "rule_flag": signals.get("rule_flag"),
            },
            "model": {
                "name": model.get("name"),
                "version": model.get("version"),
                "stage": model.get("stage"),
                "run_id": model.get("run_id"),
            },
            "logged_at_epoch": time.time(),
        }

        _firestore_client().collection(REQUEST_LOG_COLLECTION).document(request_id).set(document)
        return request_id
    except Exception as exc:
        print(f"request_logger_error={exc}")
        return None
