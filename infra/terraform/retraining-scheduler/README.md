# Terraform: Retraining Scheduler

This stack provisions automated retraining:

- Cloud Run Job that runs `python train.py`.
- Cloud Scheduler job that triggers the job every Sunday at midnight.
- Service accounts and IAM needed to build, pull, and trigger the job.

## Deploy

From the repository root:

```powershell
Copy-Item infra\terraform\retraining-scheduler\terraform.tfvars.example infra\terraform\retraining-scheduler\terraform.tfvars
.\scripts\deploy-retraining-scheduler.ps1 -ProjectId "momo-fraud" -AutoApprove
```

## Manual Run

```powershell
gcloud run jobs execute momo-fraud-retraining --region us-central1 --project momo-fraud
```

## Firestore Threshold Trigger

Cloud Scheduler cannot directly trigger only when Firestore reaches a count of
new logged requests. To support that later, add a small monitor job or Cloud
Function that counts new documents in `prediction_requests`, compares the count
to a threshold, then calls the Cloud Run Job run endpoint.

## Important Model Serving Note

Scheduled retraining updates MLflow and the evaluation gate. The current live
prediction API still uses model artifacts baked into its container image. To make
retraining update live predictions automatically, the next improvement is either
loading the Production model from MLflow/Cloud Storage at API startup or
triggering an API rebuild/redeploy after successful promotion.
