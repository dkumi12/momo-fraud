import pickle, json, os, time
import numpy as np
from collections import defaultdict
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response

BASE = os.path.dirname(os.path.abspath(__file__))
app  = FastAPI(title="MoMo Fraud Detection")

def read_html(name):
    with open(os.path.join(BASE, "templates", name), encoding="utf-8") as f:
        return f.read()

with open(os.path.join(BASE, "models", "xgboost.pkl"), "rb") as f:
    xgb = pickle.load(f)
with open(os.path.join(BASE, "models", "caps.json")) as f:
    caps = json.load(f)
with open(os.path.join(BASE, "models", "feature_columns.json")) as f:
    FEATURE_COLS = json.load(f)

threshold_path = os.path.join(BASE, "models", "threshold.json")
_threshold_data  = json.load(open(threshold_path)) if os.path.exists(threshold_path) else {}
FRAUD_THRESHOLD  = float(_threshold_data.get("threshold", 0.5))
MODEL_RUN_ID     = _threshold_data.get("run_id", "local")
MODEL_VERSION    = _threshold_data.get("model_version", "v1.0")

MONETARY = ["amount","oldbalanceOrg","newbalanceOrig",
            "oldbalanceDest","newbalanceDest",
            "errorBalanceOrig","errorBalanceDest"]

SENDER_BALANCE = 12500.0

RECIPIENTS = {
    "shoprite":  {"name": "Shoprite Ghana",     "type": "PAYMENT",  "is_merchant": 1, "old_dest": 0.0},
    "mtn_shop":  {"name": "MTN Service Center", "type": "PAYMENT",  "is_merchant": 1, "old_dest": 0.0},
    "kwame":     {"name": "Kwame Asante",       "type": "TRANSFER", "is_merchant": 0, "old_dest": 8500.0},
    "abena":     {"name": "Abena Mensah",       "type": "TRANSFER", "is_merchant": 0, "old_dest": 22000.0},
    "cashpoint": {"name": "Cash Point Agent",   "type": "CASH_OUT", "is_merchant": 0, "old_dest": 150000.0},
    "unknown":   {"name": "Unknown Account",    "type": "TRANSFER", "is_merchant": 0, "old_dest": 0.0},
}

TYPE_MAP = {"PAYMENT":0, "TRANSFER":1, "CASH_OUT":2, "CASH_IN":3, "DEBIT":4}

session_log: dict[str, list] = defaultdict(list)
VELOCITY_WINDOW = 300
MAX_TX_COUNT    = 3
MAX_CUMULATIVE  = SENDER_BALANCE * 0.5
MAX_SAME_DEST   = 2


def _risk_level(prob: float) -> str:
    if prob >= 0.8:
        return "high"
    if prob >= 0.5:
        return "medium"
    return "low"


def _model_block() -> dict:
    return {
        "name":    "xgboost_momo_baseline",
        "version": MODEL_VERSION,
        "stage":   "Production",
        "run_id":  MODEL_RUN_ID,
    }


def check_velocity(session_id: str, amount: float, recipient: str) -> dict:
    now     = time.time()
    history = session_log[session_id]
    history[:] = [t for t in history if now - t["time"] < VELOCITY_WINDOW]

    count      = len(history)
    cumulative = sum(t["amount"] for t in history) + amount
    same_dest  = sum(1 for t in history if t["recipient"] == recipient)

    flag, reason = False, ""

    if count + 1 > MAX_TX_COUNT:
        flag   = True
        reason = (f"Smurfing detected: {count + 1} transactions within 5 minutes. "
                  f"Fraudsters split large transfers into small ones to avoid detection.")
    elif cumulative > MAX_CUMULATIVE:
        flag   = True
        reason = (f"Cumulative transfer of GHS {cumulative:,.2f} within 5 minutes "
                  f"exceeds the allowed limit of GHS {MAX_CUMULATIVE:,.2f}.")
    elif same_dest + 1 > MAX_SAME_DEST:
        flag   = True
        reason = (f"Multiple transfers to the same recipient ({RECIPIENTS.get(recipient, {}).get('name', recipient)}) "
                  f"in a short period — suspicious pattern detected.")

    history.append({"time": now, "amount": amount, "recipient": recipient})
    return {"velocity_flag": flag, "reason": reason, "tx_count": count + 1, "cumulative": round(cumulative, 2)}


def _apply_caps_and_log(raw: dict) -> dict:
    for col in MONETARY:
        raw[col] = float(np.clip(raw[col], caps[col]["p01"], caps[col]["p99"]))
    for col in MONETARY:
        raw[f"log_{col}"] = float(np.log1p(max(raw[col], 0)))
    return raw


def build_feature_payload(amount: float, recipient_key: str) -> dict:
    r        = RECIPIENTS[recipient_key]
    tx_type  = r["type"]
    old_orig = SENDER_BALANCE
    old_dest = r["old_dest"]
    new_orig = max(0.0, old_orig - amount) if tx_type in ("TRANSFER","CASH_OUT","PAYMENT","DEBIT") else old_orig + amount
    new_dest = 0.0 if recipient_key == "unknown" else old_dest + amount

    raw = {
        "step":             200,
        "type":             TYPE_MAP[tx_type],
        "amount":           amount,
        "oldbalanceOrg":    old_orig,
        "newbalanceOrig":   new_orig,
        "oldbalanceDest":   old_dest,
        "newbalanceDest":   new_dest,
        "isDestMerchant":   r["is_merchant"],
        "errorBalanceOrig": new_orig + amount - old_orig,
        "errorBalanceDest": old_dest + amount - new_dest,
    }
    return _apply_caps_and_log(raw)


def build_feature_payload_from_json(body: dict) -> dict:
    tx_type  = body["type"]
    amount   = float(body["amount"])
    old_orig = float(body["oldbalanceOrg"])
    new_orig = float(body["newbalanceOrig"])
    old_dest = float(body["oldbalanceDest"])
    new_dest = float(body["newbalanceDest"])

    raw = {
        "step":             int(body.get("step", 200)),
        "type":             TYPE_MAP[tx_type],
        "amount":           amount,
        "oldbalanceOrg":    old_orig,
        "newbalanceOrig":   new_orig,
        "oldbalanceDest":   old_dest,
        "newbalanceDest":   new_dest,
        "isDestMerchant":   int(body.get("is_dest_merchant", False)),
        "errorBalanceOrig": new_orig + amount - old_orig,
        "errorBalanceDest": old_dest + amount - new_dest,
    }
    return _apply_caps_and_log(raw)


def score_features(raw: dict, amount: float, balance: float, recipient_key: str = "") -> dict:
    X          = np.array([[raw[col] for col in FEATURE_COLS]])
    model_prob = float(xgb.predict_proba(X)[0][1])
    model_flag = model_prob >= FRAUD_THRESHOLD
    rule_flag  = False
    reason     = "No fraud signal detected by the model."
    r          = RECIPIENTS.get(recipient_key, {})
    tx_type    = r.get("type", "")

    if amount > balance:
        rule_flag  = True
        model_prob = max(model_prob, 0.99)
        reason     = "Amount exceeds available balance."
    elif tx_type in ("TRANSFER","CASH_OUT") and recipient_key == "unknown":
        rule_flag  = True
        model_prob = max(model_prob, 0.99)
        reason     = "Transfer to unknown account — destination balance mismatch detected."
    elif tx_type in ("TRANSFER","CASH_OUT") and amount >= balance * 0.90:
        rule_flag  = True
        model_prob = max(model_prob, 0.95)
        reason     = "Transaction would drain nearly all available funds."
    elif model_flag:
        reason = "Model score crossed the fraud threshold."

    return {
        "fraud":      int(model_flag or rule_flag),
        "probability": model_prob,
        "reason":      reason,
        "model_flag":  model_flag,
        "rule_flag":   rule_flag,
    }


# ── Endpoints ─────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "momo-fraud-api", "model_loaded": True}


@app.get("/model-info")
async def model_info():
    return {**_model_block(), "features": FEATURE_COLS}


@app.get("/", response_class=HTMLResponse)
async def home():
    return HTMLResponse(read_html("index.html"))


@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)


@app.post("/reset")
async def reset_session(request: Request):
    form       = await request.form()
    session_id = form.get("session_id", "demo")
    session_log[session_id] = []
    return {"reset": True}


@app.post("/predict")
async def predict(request: Request):
    content_type = request.headers.get("content-type", "")

    try:
        # ── JSON path (production clients) ────────────────────
        if "application/json" in content_type:
            body       = await request.json()
            amount     = float(body["amount"])
            session_id = body.get("session_id", "default")
            tx_id      = body.get("transaction_id", f"txn_{int(time.time())}")
            recipient  = body.get("recipient_id", "unknown")

            if amount <= 0:
                return {"error": "validation_error", "message": "amount must be greater than 0",
                        "fields": {"amount": "must be greater than 0"}}

            raw        = build_feature_payload_from_json(body)
            assessment = score_features(raw, amount, float(body.get("oldbalanceOrg", amount)), recipient)
            velocity   = check_velocity(session_id, amount, recipient)

            is_fraud = assessment["fraud"] == 1 or velocity["velocity_flag"]
            prob     = assessment["probability"]
            reason   = velocity["reason"] if velocity["velocity_flag"] else assessment["reason"]
            if velocity["velocity_flag"]:
                prob = max(prob, 0.97)

            return {
                "transaction_id": tx_id,
                "prediction":     "FRAUD" if is_fraud else "LEGITIMATE",
                "fraud":           int(is_fraud),
                "probability":     round(prob, 4),
                "threshold":       FRAUD_THRESHOLD,
                "risk_level":      _risk_level(prob),
                "reason":          reason,
                "signals": {
                    "model_flag":    assessment["model_flag"],
                    "velocity_flag": velocity["velocity_flag"],
                    "rule_flag":     assessment["rule_flag"],
                },
                "model": _model_block(),
            }

        # ── Form path (HTML demo) ─────────────────────────────
        form       = await request.form()
        amount     = float(form["amount"])
        recipient  = form["recipient"]
        session_id = form.get("session_id", "demo")

        if amount <= 0:
            return {"error": "Amount must be greater than 0"}

        raw        = build_feature_payload(amount, recipient)
        assessment = score_features(raw, amount, SENDER_BALANCE, recipient)
        velocity   = check_velocity(session_id, amount, recipient)

        is_fraud = assessment["fraud"] == 1 or velocity["velocity_flag"]
        prob     = assessment["probability"]
        reason   = velocity["reason"] if velocity["velocity_flag"] else assessment["reason"]
        if velocity["velocity_flag"]:
            prob = max(prob, 0.97)

        r = RECIPIENTS[recipient]
        return {
            "prediction":     "FRAUD" if is_fraud else "LEGITIMATE",
            "fraud":           int(is_fraud),
            "probability":     round(prob * 100, 2),
            "threshold":       FRAUD_THRESHOLD,
            "risk_level":      _risk_level(prob),
            "amount":          f"{amount:,.2f}",
            "recipient_name":  r["name"],
            "tx_type":         r["type"],
            "sender_balance":  f"{SENDER_BALANCE:,.2f}",
            "new_balance":     f"{max(0.0, SENDER_BALANCE - amount):,.2f}",
            "reason":          reason,
            "tx_count":        velocity["tx_count"],
            "cumulative":      f"{velocity['cumulative']:,.2f}",
            "velocity_flag":   velocity["velocity_flag"],
            "signals": {
                "model_flag":    assessment["model_flag"],
                "velocity_flag": velocity["velocity_flag"],
                "rule_flag":     assessment["rule_flag"],
            },
            "model": _model_block(),
        }

    except Exception as e:
        return {"error": "prediction_error", "message": str(e)}
