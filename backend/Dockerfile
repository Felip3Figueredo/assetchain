FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
COPY blockchain/artifacts-export/AssetToken.json /app/artifact/AssetToken.json
ENV ARTIFACT_PATH=/app/artifact/AssetToken.json
EXPOSE 8000
CMD ["sh", "-c", "python -m app.bootstrap && if [ \"$SEED_DEMO\" = \"true\" ]; then python -m app.seed --demo; else python -m app.seed; fi && exec uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000"]
