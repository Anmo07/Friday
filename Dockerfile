# Root compatibility Dockerfile.
# Canonical runtime Dockerfile lives at veritas-ai/Dockerfile.
FROM python:3.11-slim

WORKDIR /app/veritas-ai

COPY veritas-ai/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt

COPY veritas-ai /app/veritas-ai

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
