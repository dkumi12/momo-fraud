"""
MoMo Fraud Detection - XGBoost training pipeline with evaluation gate.
"""
import json
import os
import pickle
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import mlflow
import numpy as np
import pandas as pd
import requests
from imblearn.over_sampling import SMOTE
from mlflow.tracking import MlflowClient
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

from features import apply_features, fit_caps, load_clean_data


SEED = 42
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "https://momo-mlflow-7e2lu7f7ta-uc.a.run.app")
MLFLOW_EXPERIMENT   = os.getenv("MLFLOW_EXPERIMENT_NAME", "momo-fraud")
TRAINING_DATA_URI   = os.getenv("TRAINING_DATA_URI", "Pay-sim.csv")
PREDICTION_API_URL  = os.getenv("PREDICTION_API_URL", "").rstrip("/")
MODEL_NAME          = "xgboost_momo_baseline"
MODEL_ARTIFACT_PATH = "model"


def best_threshold(y_true: pd.Series, y_prob: np.ndarray) -> tuple[float, float]:
    candidates = np.linspace(0.05, 0.95, 181)
    scores = [(t, f1_score(y_true, y_prob >= t)) for t in candidates]
    return max(scores, key=lambda item: item[1])


def get_production_metrics(client: MlflowClient) -> dict | None:
    """Return metrics of the current Production run, or None if none exists."""
    experiment = client.get_experiment_by_name(MLFLOW_EXPERIMENT)
    if not experiment:
        return None
    runs = client.search_runs(
        experiment_ids=[experiment.experiment_id],
        filter_string="tags.stage = 'Production'",
        order_by=["start_time DESC"],
        max_results=1,
    )
    return runs[0].data.metrics if runs else None


def get_storage_client():
    from google.cloud import storage

    return storage.Client()


def resolve_training_data(data_uri: str = TRAINING_DATA_URI) -> str:
    """Return a local CSV path, downloading from Cloud Storage when needed."""
    if data_uri.startswith("gs://"):
        parsed = urlparse(data_uri)
        bucket_name = parsed.netloc
        object_name = parsed.path.lstrip("/")
        if not bucket_name or not object_name:
            raise ValueError(f"Invalid TRAINING_DATA_URI: {data_uri}")

        local_path = Path(tempfile.gettempdir()) / Path(object_name).name
        get_storage_client().bucket(bucket_name).blob(object_name).download_to_filename(local_path)
        print(f"      Downloaded training data from {data_uri} -> {local_path}")
        return str(local_path)

    local_path = Path(data_uri)
    if not local_path.exists():
        raise FileNotFoundError(
            f"Training data not found at {data_uri}. Set TRAINING_DATA_URI to a gs:// bucket object."
        )
    return str(local_path)


def evaluation_gate(client: MlflowClient, new_run_id: str, new_metrics: dict) -> bool:
    """
    Compare new model against the live Production model.
    Promote only if strictly better on test_f1. Returns True if promoted.
    """
    print("\n  -- Evaluation Gate --")
    prod_metrics = get_production_metrics(client)

    if prod_metrics is None:
        client.set_tag(new_run_id, "stage", "Production")
        print("  No existing Production model found. New model promoted to Production.")
        return True

    new_f1  = new_metrics.get("test_f1", 0)
    prod_f1 = prod_metrics.get("test_f1", 0)
    new_auc  = new_metrics.get("test_auc", 0)
    prod_auc = prod_metrics.get("test_auc", 0)

    print(f"  Current Production -> F1: {prod_f1:.4f} | AUC: {prod_auc:.4f}")
    print(f"  New model          -> F1: {new_f1:.4f} | AUC: {new_auc:.4f}")

    if new_f1 > prod_f1 or (new_f1 == prod_f1 and new_auc > prod_auc):
        # Remove Production tag from previous runs
        experiment = client.get_experiment_by_name(MLFLOW_EXPERIMENT)
        old_runs = client.search_runs(
            experiment_ids=[experiment.experiment_id],
            filter_string="tags.stage = 'Production'",
        )
        for run in old_runs:
            client.delete_tag(run.info.run_id, "stage")

        client.set_tag(new_run_id, "stage", "Production")
        print(f"  PROMOTED: New model is strictly better (F1 {new_f1:.4f} > {prod_f1:.4f}).")
        return True
    else:
        print(f"  NOT PROMOTED: Current Production model is equal or better.")
        return False


def notify_api_reload(api_url: str = PREDICTION_API_URL) -> dict | None:
    """Tell the live API to hot-load the latest Production model from MLflow."""
    if not api_url:
        print("  API reload skipped: PREDICTION_API_URL is not set.")
        return None

    before = requests.get(f"{api_url}/model-info", timeout=30)
    before.raise_for_status()
    before_info = before.json()

    reload_response = requests.post(f"{api_url}/reload-model", json={}, timeout=120)
    reload_response.raise_for_status()
    reload_info = reload_response.json()
    if reload_info.get("error"):
        raise RuntimeError(f"API reload failed: {reload_info['error']}")

    after = requests.get(f"{api_url}/model-info", timeout=30)
    after.raise_for_status()
    after_info = after.json()

    print("\n  -- API Hot Reload --")
    print(f"  Before: version={before_info.get('version')} run_id={before_info.get('run_id')}")
    print(f"  After : version={after_info.get('version')} run_id={after_info.get('run_id')}")
    return {"before": before_info, "reload": reload_info, "after": after_info}


def log_baseline(name: str, model, X_train, y_train, X_val, y_val, X_test, y_test, params: dict):
    """Train a baseline model and log it as its own MLflow run."""
    with mlflow.start_run(run_name=name):
        mlflow.log_params({**params, "model": name})
        model.fit(X_train, y_train)

        val_prob          = model.predict_proba(X_val)[:, 1]
        threshold, val_f1 = best_threshold(y_val, val_prob)

        y_prob   = model.predict_proba(X_test)[:, 1]
        y_pred   = (y_prob >= threshold).astype(int)
        test_f1  = f1_score(y_test, y_pred)
        test_auc = roc_auc_score(y_test, y_prob)

        mlflow.log_metrics({
            "val_f1":    round(val_f1, 4),
            "threshold": round(threshold, 4),
            "test_f1":   round(test_f1, 4),
            "test_auc":  round(test_auc, 4),
        })
        mlflow.set_tag("model_name", name)
        print(f"  {name:25s} | F1: {test_f1:.4f} | AUC: {test_auc:.4f} | Threshold: {threshold:.3f}")


def main() -> None:
    os.makedirs("models", exist_ok=True)

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(MLFLOW_EXPERIMENT)
    client = MlflowClient()

    print("=" * 55)
    print("  MoMo Fraud Detection - XGBoost Training Pipeline")
    print("=" * 55)
    print(f"  MLflow: {MLFLOW_TRACKING_URI}")
    print(f"  Training data: {TRAINING_DATA_URI}")

    print("\n[1/7] Loading and cleaning data...")
    training_data_path = resolve_training_data()
    X, y = load_clean_data(training_data_path)
    print(f"      Rows: {len(X):,} | Fraud rate: {y.mean() * 100:.2f}%")

    print("[2/7] Creating train/validation/test split...")
    X_train_full, X_test, y_train_full, y_test = train_test_split(
        X, y, test_size=0.2, random_state=SEED, stratify=y
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_train_full, y_train_full, test_size=0.25, random_state=SEED, stratify=y_train_full,
    )

    print("[3/7] Fitting preprocessing on train split only...")
    caps    = fit_caps(X_train)
    X_train = apply_features(X_train, caps)
    X_val   = apply_features(X_val, caps)
    X_test  = apply_features(X_test, caps)

    print("[4/7] Applying SMOTE to the train split...")
    X_train_sm, y_train_sm = SMOTE(random_state=SEED).fit_resample(X_train, y_train)
    print(f"      After SMOTE: {pd.Series(y_train_sm).value_counts().to_dict()}")

    print("\n[5/7] Logging baseline models to MLflow...")
    log_baseline(
        "logistic_regression",
        LogisticRegression(max_iter=1000, random_state=SEED),
        X_train_sm, y_train_sm, X_val, y_val, X_test, y_test,
        {"max_iter": 1000},
    )
    log_baseline(
        "random_forest",
        RandomForestClassifier(n_estimators=100, random_state=SEED, n_jobs=-1),
        X_train_sm, y_train_sm, X_val, y_val, X_test, y_test,
        {"n_estimators": 100},
    )

    xgb_params = {
        "n_estimators": 160,
        "max_depth": 5,
        "learning_rate": 0.08,
        "subsample": 0.9,
        "colsample_bytree": 0.9,
    }

    print("\n[6/7] Training XGBoost (production candidate)...")
    with mlflow.start_run(run_name="xgboost_baseline") as run:
        mlflow.log_params({
            **xgb_params,
            "seed": SEED,
            "smote": True,
            "model": "xgboost",
            "training_data_uri": TRAINING_DATA_URI,
        })

        model = XGBClassifier(**xgb_params, random_state=SEED, eval_metric="logloss")
        model.fit(X_train_sm, y_train_sm)

        val_prob          = model.predict_proba(X_val)[:, 1]
        threshold, val_f1 = best_threshold(y_val, val_prob)

        y_prob   = model.predict_proba(X_test)[:, 1]
        y_pred   = (y_prob >= threshold).astype(int)
        test_f1  = f1_score(y_test, y_pred)
        test_auc = roc_auc_score(y_test, y_prob)

        new_metrics = {
            "val_f1":    round(val_f1, 4),
            "threshold": round(threshold, 4),
            "test_f1":   round(test_f1, 4),
            "test_auc":  round(test_auc, 4),
        }
        mlflow.log_metrics(new_metrics)
        mlflow.set_tag("model_name", MODEL_NAME)
        mlflow.set_tag("artifact_path", MODEL_ARTIFACT_PATH)

        run_id = run.info.run_id
        print(f"      Threshold: {threshold:.3f} | F1: {test_f1:.4f} | AUC: {test_auc:.4f}")
        print(f"      MLflow run: {run_id}")

        # ── Evaluation Gate ───────────────────────────────────
        promoted = evaluation_gate(client, run_id, new_metrics)

        print("\n[7/7] Saving and logging model artifacts...")
        model_version = run_id[:8]
        with open("models/xgboost.pkl", "wb") as f:
            pickle.dump(model, f)
        with open("models/caps.json", "w") as f:
            json.dump(caps, f, indent=2)
        with open("models/feature_columns.json", "w") as f:
            json.dump(X_train.columns.tolist(), f, indent=2)
        with open("models/threshold.json", "w") as f:
            json.dump({
                "threshold":     float(threshold),
                "validation_f1": float(val_f1),
                "run_id":        run_id,
                "model_version": model_version,
                "promoted":      promoted,
            }, f, indent=2)
        mlflow.log_artifacts("models", artifact_path=MODEL_ARTIFACT_PATH)
        mlflow.set_tag("model_version", model_version)

        if promoted:
            notify_api_reload()

    print("\n" + "=" * 55)
    print("  Final Test Results (XGBoost)")
    print("=" * 55)
    print("Confusion matrix:", confusion_matrix(y_test, y_pred).tolist())
    print(classification_report(y_test, y_pred, target_names=["Non-Fraud", "Fraud"]))
    print(f"  F1-Score : {test_f1:.4f}")
    print(f"  ROC-AUC  : {test_auc:.4f}")
    print(f"  Promoted : {promoted}")
    print("  Model saved -> models/xgboost.pkl")
    print(f"  MLflow    -> {MLFLOW_TRACKING_URI}")


if __name__ == "__main__":
    main()
