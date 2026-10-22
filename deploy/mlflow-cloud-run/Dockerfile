FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

RUN pip install --no-cache-dir \
    "mlflow==2.14.3" \
    "psycopg2-binary==2.9.9" \
    "google-cloud-storage==2.17.0"

EXPOSE 8080

CMD ["sh", "-c", "mlflow server --host 0.0.0.0 --port ${PORT:-8080} --backend-store-uri \"$BACKEND_STORE_URI\" --default-artifact-root \"$ARTIFACT_ROOT\" --serve-artifacts"]
