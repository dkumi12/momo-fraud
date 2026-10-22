# Known Issues and Roadmap

## Current Limitations

1. **Prototype data only.** The included workflow uses PaySim-style simulated data, so model quality has not been established on live mobile-money traffic.
2. **No published reproducible metrics report.** Training logs metrics to MLflow, but the repository does not yet include a frozen experiment report with dataset version, split sizes, precision, recall, F1, ROC-AUC, and confusion matrix.
3. **In-memory velocity state.** Session-level velocity checks reset when the API restarts and are not coordinated across multiple service instances.
4. **No production authentication layer.** Public deployment requires authenticated access, rate limits, request validation, and least-privilege service identities.
5. **No drift or calibration monitoring.** The project lacks automated alerts for input shifts, score drift, threshold health, or model calibration.
6. **No fairness or operational-impact analysis.** Real deployment would need approved demographic and operational evaluation, especially false-positive review.
7. **Demo assets are incomplete.** The repository does not yet include screenshots, a short walkthrough, or a recorded API demonstration.

## Recommended Next Steps

1. Produce a versioned MLflow evaluation report and add the key figures to the README.
2. Add an API smoke test that loads the local model and exercises `/health`, `/model-info`, and `/predict`.
3. Move velocity/session state to a durable shared store before horizontally scaling the service.
4. Add authentication, rate limits, structured error handling, and monitoring to the Cloud Run deployment path.
5. Document dataset provenance, retention, access controls, and a process for retraining approval and rollback.
6. Capture a brief demo GIF or screenshots after the local application is verified.

## Publication Checklist

- Never publish real transaction data, `.env` files, Terraform state, service-account material, or API credentials.
- Confirm `Pay-sim.csv` is intentionally excluded from the public history before pushing.
- Remove or explain unused scaffolding before presenting the repository as complete.
- Keep this file current as limitations are resolved.
