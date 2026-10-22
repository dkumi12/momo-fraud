# Retraining Job Container

This directory packages the ML team's `train.py` script as a Cloud Run Job.

The job downloads the latest training CSV from Cloud Storage, runs feature
engineering, trains the model, logs metrics and model artifacts to MLflow,
applies the evaluation gate, and calls the prediction API's `/reload-model`
endpoint when a new model is promoted.

Deploy through:

```powershell
.\scripts\deploy-retraining-scheduler.ps1 -ProjectId "momo-fraud" -AutoApprove
```

After a successful promotion, the API reloads the new Production artifacts from
MLflow without restarting the Cloud Run container. Check `/model-info` to verify
the active run id and version.
