"""
MoMo Fraud Detection - XGBoost training pipeline with evaluation gate.
"""
import json
import os
import pickle

import mlflow
import numpy as np
import pandas as pd
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
MODEL_NAME          = "xgboost_momo_baseline"


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

    print("\n[1/7] Loading and cleaning data...")
    X, y = load_clean_data("Pay-sim.csv")
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
        mlflow.log_params({**xgb_params, "seed": SEED, "smote": True, "model": "xgboost"})

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
        mlflow.set_tag("artifact_local_path", "models/xgboost.pkl")

        run_id = run.info.run_id
        print(f"      Threshold: {threshold:.3f} | F1: {test_f1:.4f} | AUC: {test_auc:.4f}")
        print(f"      MLflow run: {run_id}")

        # ── Evaluation Gate ───────────────────────────────────
        promoted = evaluation_gate(client, run_id, new_metrics)

    print("\n[7/7] Saving artifacts locally...")
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
            "model_version": "v1.0",
            "promoted":      promoted,
        }, f, indent=2)

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
