"""
MoMo Fraud Detection - XGBoost training pipeline.
"""
import json
import os
import pickle

import mlflow
import mlflow.xgboost
import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
from sklearn.metrics import classification_report, confusion_matrix, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier


SEED = 42
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "https://momo-mlflow-7e2lu7f7ta-uc.a.run.app")
MLFLOW_EXPERIMENT   = os.getenv("MLFLOW_EXPERIMENT_NAME", "momo-fraud")
MODEL_NAME          = "xgboost_momo_baseline"

MONETARY = [
    "amount",
    "oldbalanceOrg",
    "newbalanceOrig",
    "oldbalanceDest",
    "newbalanceDest",
    "errorBalanceOrig",
    "errorBalanceDest",
]
TYPE_MAP = {"PAYMENT": 0, "TRANSFER": 1, "CASH_OUT": 2, "CASH_IN": 3, "DEBIT": 4}


def load_clean_data(path: str) -> tuple[pd.DataFrame, pd.Series]:
    df = pd.read_csv(path)
    df = df[df["amount"] > 0].drop_duplicates().reset_index(drop=True)
    df["isDestMerchant"] = (df["nameDest"].str[0] == "M").astype(int)
    df = df.drop(columns=["nameOrig", "nameDest", "isFlaggedFraud"])
    df["type"] = df["type"].map(TYPE_MAP)
    df["errorBalanceOrig"] = df["newbalanceOrig"] + df["amount"] - df["oldbalanceOrg"]
    df["errorBalanceDest"] = df["oldbalanceDest"] + df["amount"] - df["newbalanceDest"]
    y = df.pop("isFraud")
    return df, y


def fit_caps(X_train: pd.DataFrame) -> dict:
    return {
        col: {
            "p01": float(X_train[col].quantile(0.01)),
            "p99": float(X_train[col].quantile(0.99)),
        }
        for col in MONETARY
    }


def apply_features(X: pd.DataFrame, caps: dict) -> pd.DataFrame:
    X = X.copy()
    for col in MONETARY:
        X[col] = X[col].clip(lower=caps[col]["p01"], upper=caps[col]["p99"])
    for col in MONETARY:
        X[f"log_{col}"] = np.log1p(X[col].clip(lower=0))
    return X


def best_threshold(y_true: pd.Series, y_prob: np.ndarray) -> tuple[float, float]:
    candidates = np.linspace(0.05, 0.95, 181)
    scores = [(threshold, f1_score(y_true, y_prob >= threshold)) for threshold in candidates]
    return max(scores, key=lambda item: item[1])


def main() -> None:
    os.makedirs("models", exist_ok=True)

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(MLFLOW_EXPERIMENT)

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
        X_train_full,
        y_train_full,
        test_size=0.25,
        random_state=SEED,
        stratify=y_train_full,
    )

    print("[3/7] Fitting preprocessing on train split only...")
    caps = fit_caps(X_train)
    X_train = apply_features(X_train, caps)
    X_val   = apply_features(X_val, caps)
    X_test  = apply_features(X_test, caps)

    print("[4/7] Applying SMOTE to the train split...")
    X_train_sm, y_train_sm = SMOTE(random_state=SEED).fit_resample(X_train, y_train)
    print(f"      After SMOTE: {pd.Series(y_train_sm).value_counts().to_dict()}")

    params = {
        "n_estimators": 160,
        "max_depth": 5,
        "learning_rate": 0.08,
        "subsample": 0.9,
        "colsample_bytree": 0.9,
    }

    with mlflow.start_run(run_name="xgboost_baseline"):
        mlflow.log_params({**params, "seed": SEED, "smote": True})

        print("[5/7] Training XGBoost...")
        model = XGBClassifier(**params, random_state=SEED, eval_metric="logloss")
        model.fit(X_train_sm, y_train_sm)

        print("[6/7] Selecting validation threshold...")
        val_prob = model.predict_proba(X_val)[:, 1]
        threshold, val_f1 = best_threshold(y_val, val_prob)
        print(f"      Threshold: {threshold:.3f} | Validation F1: {val_f1:.4f}")

        y_prob = model.predict_proba(X_test)[:, 1]
        y_pred = (y_prob >= threshold).astype(int)
        test_f1  = f1_score(y_test, y_pred)
        test_auc = roc_auc_score(y_test, y_prob)

        mlflow.log_metrics({
            "val_f1":    round(val_f1, 4),
            "threshold": round(threshold, 4),
            "test_f1":   round(test_f1, 4),
            "test_auc":  round(test_auc, 4),
        })
        mlflow.set_tag("model_name", MODEL_NAME)
        mlflow.set_tag("artifact_local_path", "models/xgboost.pkl")

        run_id = mlflow.active_run().info.run_id
        print(f"      MLflow run: {run_id}")

        print("[7/7] Saving artifacts...")
        with open("models/xgboost.pkl", "wb") as f:
            pickle.dump(model, f)
        with open("models/caps.json", "w") as f:
            json.dump(caps, f, indent=2)
        with open("models/feature_columns.json", "w") as f:
            json.dump(X_train.columns.tolist(), f, indent=2)
        with open("models/threshold.json", "w") as f:
            json.dump({
                "threshold":      float(threshold),
                "validation_f1":  float(val_f1),
                "run_id":         run_id,
                "model_version":  "v1.0",
            }, f, indent=2)

    print("\n" + "=" * 55)
    print("  Final Test Results")
    print("=" * 55)
    print("Confusion matrix:", confusion_matrix(y_test, y_pred).tolist())
    print(classification_report(y_test, y_pred, target_names=["Non-Fraud", "Fraud"]))
    print(f"  F1-Score : {test_f1:.4f}")
    print(f"  ROC-AUC  : {test_auc:.4f}")
    print("  Model saved -> models/xgboost.pkl")
    print(f"  MLflow run logged -> {MLFLOW_TRACKING_URI}")


if __name__ == "__main__":
    main()
