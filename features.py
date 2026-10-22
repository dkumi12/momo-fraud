"""
Shared feature engineering functions used by train.py and app.py.
"""
import numpy as np
import pandas as pd


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
