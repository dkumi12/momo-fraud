# Model Card: MoMo Fraud Detection Prototype

## Model Details

| Field | Value |
| --- | --- |
| Primary model | XGBoost binary classifier |
| Current local artifact | `models/xgboost.pkl` |
| Artifact metadata | `models/threshold.json` |
| Model identifier | `xgboost_momo_baseline` |
| Local version label | `v1.0` |
| Decision threshold | `0.735` |
| Tracking | MLflow |
| Serving | FastAPI, with Cloud Run deployment assets |

The training pipeline also logs logistic-regression and random-forest baselines. It uses a stratified train/validation/test split, fits feature caps on the training split, applies SMOTE only to that split, and selects the operating threshold on validation data.

## Intended Use

This prototype is intended for technical demonstration, experimentation, and fraud-operations triage research using PaySim-style transaction data. It can help illustrate how a risk-scoring service, model registry, and deployment workflow fit together.

It is **not** intended to autonomously deny payments, freeze accounts, make customer eligibility decisions, or operate on live financial data without governance, validation, monitoring, and human review.

## Inputs and Outputs

The model uses transaction features such as transaction type, amount, sender and destination balances, balance-error features, and merchant indicators. The service returns a fraud classification, probability, risk level, threshold, explanatory signal flags, and loaded-model metadata.

The API may also apply velocity and rule-based signals. Those signals are service-level controls, not learned model features, and should be evaluated separately from model performance.

## Evaluation and Promotion

The training process records validation F1, test F1, and test ROC-AUC in MLflow. A candidate is promoted only when it improves test F1 over the model tagged `Production`; where F1 is equal, it must improve test AUC.

The checked-in threshold metadata reports a validation F1 of approximately `0.9973`. This result is tied to the local PaySim-style data and must not be generalized to real-world transaction fraud detection. A portfolio-ready release should publish a reproducible evaluation report with precision, recall, F1, ROC-AUC, confusion matrix, data split details, and false-positive analysis.

## Limitations and Risks

- The available data is simulated and may not represent real customer behavior, fraud patterns, data quality, or class prevalence.
- Threshold selection can shift false-positive and false-negative outcomes; these costs must be set with fraud-operations stakeholders.
- The project does not establish fairness, calibration, robustness, or drift performance across real customer groups.
- Velocity checks use in-memory session state in the prototype and are not a durable, distributed transaction-control system.
- Scores and explanations are decision-support signals, not evidence of fraud.

## Maintenance Requirements

Before real deployment, establish data governance, access controls, retention policies, audit logging, incident response, drift monitoring, performance review, human escalation, and a documented rollback procedure. Retraining should use approved data and compare against a held-out evaluation set before promotion.
