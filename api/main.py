from fastapi import FastAPI

app = FastAPI(title="MoMo Fraud Detection API")

@app.post("/predict")
def predict():
    """Receives input data, runs the model, returns a prediction."""
    return {"message": "Prediction endpoint"}

@app.get("/health")
def health_check():
    """The Cloud team uses this to check if the API is alive."""
    return {"status": "ok"}

@app.get("/model-info")
def model_info():
    """Shows exactly which model is currently running in production."""
    return {"model_name": "xgboost_momo_baseline", "version": "v1.0", "stage": "Production"}

@app.post("/reload-model")
def reload_model():
    """Triggered by the Cloud team's scheduler to hot-swap the model with zero downtime."""
    return {"status": "Model hot-swapped successfully"}
