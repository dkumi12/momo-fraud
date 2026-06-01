# Dockerfile for FastAPI Prediction Service
FROM python:3.10-slim
WORKDIR /app
COPY . /app
RUN pip install fastapi uvicorn pandas scikit-learn mlflow
EXPOSE 8080
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]
