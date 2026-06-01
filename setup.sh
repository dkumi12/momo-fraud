#!/bin/bash

echo "🚀 Bootstrapping Cloud × ML MoMo Fraud Detection Project..."

# 1. Create the required directory structure
mkdir -p src
mkdir -p api
mkdir -p notebooks
mkdir -p .github/workflows

# 2. Create the ML Team's core files
# features.py: Must contain ALL feature engineering to prevent training-serving skew
# train.py: The standalone script that trains, evaluates, logs to MLflow, and promotes
touch src/features.py
touch src/train.py
touch notebooks/01_EDA_PaySim.ipynb

# 3. Create the API (Serving) files with the 4 mandatory endpoints
cat << 'EOF' > api/main.py
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
EOF

# Create the Dockerfile for the ML Team's API
cat << 'EOF' > api/Dockerfile
# Dockerfile for FastAPI Prediction Service
FROM python:3.10-slim
WORKDIR /app
COPY . /app
RUN pip install fastapi uvicorn pandas scikit-learn mlflow
EXPOSE 8080
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]
EOF

# 4. Create mandatory project documentation
# The API Contract is the most important agreement between the ML and Cloud teams
touch API_CONTRACT.md
# Required for logging data quality issues found during EDA
touch known-issues.md
# Required for documenting model inputs, outputs, and limitations
touch model_card.md

# 5. Setup environment and gitignore (Crucial for Security & Grading)
touch .env
cat << 'EOF' > .gitignore
# Environments & Secrets (Never commit credentials!)
.env
__pycache__/
*.pyc
.venv/
venv/

# MLflow local runs (Artifacts must go to Cloud Storage to be graded!)
mlruns/
mlartifacts/

# Data (Do not commit the 1GB PaySim file!)
*.csv
*.json
EOF

echo "✅ Local folder structure successfully created!"
echo " "
echo "☁️ CLOUD TEAM: Run the following gcloud commands to set up your GCP infrastructure:"
echo "----------------------------------------------------------------------------------"
echo "1. Create the MLflow Artifact Bucket (Required by Week 2):"
echo "   gcloud storage buckets create gs://momo-fraud-mlflow-artifacts --location=us-central1"
echo " "
echo "2. Create the Artifact Registry for Docker Images:"
echo "   gcloud artifacts repositories create fraud-api-repo --repository-format=docker --location=us-central1"
echo " "
echo "3. Initialize Firestore for the Request Logger (Required by Week 4):"
echo "   gcloud firestore databases create --location=us-central1"
echo "----------------------------------------------------------------------------------"
echo "Get building! 🚀"