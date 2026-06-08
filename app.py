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
FRAUD_THRESHOLD = float(json.load(open(threshold_path)).get("threshold", 0.5)) \
    if os.path.exists(threshold_path) else 0.5

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

# ── Velocity tracking (in-memory per demo session) ────────────
# Stores list of {time, amount, recipient} per session_id
session_log: dict[str, list] = defaultdict(list)

VELOCITY_WINDOW   = 300      # 5-minute sliding window (seconds)
MAX_TX_COUNT      = 3        # max transactions allowed per window
MAX_CUMULATIVE    = SENDER_BALANCE * 0.5   # GHS 6,250 cumulative cap
MAX_SAME_DEST     = 2        # max times same recipient in window


def check_velocity(session_id: str, amount: float, recipient: str) -> dict:
    now     = time.time()
    history = session_log[session_id]

    # Keep only entries within the sliding window
    history[:] = [t for t in history if now - t["time"] < VELOCITY_WINDOW]

    # Evaluate BEFORE adding this transaction
    count      = len(history)
    cumulative = sum(t["amount"] for t in history) + amount
    same_dest  = sum(1 for t in history if t["recipient"] == recipient)

    flag   = False
    reason = ""

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
        reason = (f"Multiple transfers to the same recipient ({RECIPIENTS[recipient]['name']}) "
                  f"in a short period — suspicious pattern detected.")

    # Record this transaction
    history.append({"time": now, "amount": amount, "recipient": recipient})

    return {
        "velocity_flag":  flag,
        "reason":         reason,
        "tx_count":       count + 1,
        "cumulative":     round(cumulative, 2),
    }


def build_feature_payload(amount: float, recipient_key: str) -> dict:
    r        = RECIPIENTS[recipient_key]
    tx_type  = r["type"]
    old_orig = SENDER_BALANCE
    old_dest = r["old_dest"]

    if tx_type in ("TRANSFER", "CASH_OUT", "PAYMENT", "DEBIT"):
        new_orig = max(0.0, old_orig - amount)
    else:
        new_orig = old_orig + amount

    new_dest   = 0.0 if recipient_key == "unknown" else old_dest + amount
    error_orig = new_orig + amount - old_orig
    error_dest = old_dest + amount - new_dest

    raw = {
        "step":             200,
        "type":             TYPE_MAP[tx_type],
        "amount":           amount,
        "oldbalanceOrg":    old_orig,
        "newbalanceOrig":   new_orig,
        "oldbalanceDest":   old_dest,
        "newbalanceDest":   new_dest,
        "isDestMerchant":   r["is_merchant"],
        "errorBalanceOrig": error_orig,
        "errorBalanceDest": error_dest,
    }

    for col in MONETARY:
        raw[col] = float(np.clip(raw[col], caps[col]["p01"], caps[col]["p99"]))
    for col in MONETARY:
        raw[f"log_{col}"] = float(np.log1p(max(raw[col], 0)))

    return raw


def assess_transaction(amount: float, recipient_key: str) -> dict:
    raw        = build_feature_payload(amount, recipient_key)
    X          = np.array([[raw[col] for col in FEATURE_COLS]])
    model_prob = float(xgb.predict_proba(X)[0][1])
    fraud      = int(model_prob >= FRAUD_THRESHOLD)
    reason     = "Model score crossed the fraud threshold."
    r          = RECIPIENTS[recipient_key]

    if amount > SENDER_BALANCE:
        fraud, model_prob = 1, max(model_prob, 0.99)
        reason = "Amount exceeds available balance."
    elif r["type"] in ("TRANSFER", "CASH_OUT") and recipient_key == "unknown":
        fraud, model_prob = 1, max(model_prob, 0.99)
        reason = "Transfer to unknown account — destination balance mismatch detected."
    elif r["type"] in ("TRANSFER","CASH_OUT") and amount >= SENDER_BALANCE * 0.90:
        fraud, model_prob = 1, max(model_prob, 0.95)
        reason = "Transaction would drain nearly all available funds."
    elif fraud == 0:
        reason = "No fraud signal detected by the model."

    return {"fraud": fraud, "probability": model_prob, "reason": reason}


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
    form = await request.form()
    try:
        amount     = float(form["amount"])
        recipient  = form["recipient"]
        session_id = form.get("session_id", "demo")

        if amount <= 0:
            return {"error": "Amount must be greater than 0"}

        # ── 1. Per-transaction ML + rule check ────────────────
        assessment = assess_transaction(amount, recipient)

        # ── 2. Velocity / smurfing check ──────────────────────
        velocity = check_velocity(session_id, amount, recipient)

        # Either signal can trigger fraud
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
            "amount":          f"{amount:,.2f}",
            "recipient_name":  r["name"],
            "tx_type":         r["type"],
            "sender_balance":  f"{SENDER_BALANCE:,.2f}",
            "new_balance":     f"{max(0.0, SENDER_BALANCE - amount):,.2f}",
            "reason":          reason,
            "tx_count":        velocity["tx_count"],
            "cumulative":      f"{velocity['cumulative']:,.2f}",
            "velocity_flag":   velocity["velocity_flag"],
        }
    except Exception as e:
        return {"error": str(e)}
