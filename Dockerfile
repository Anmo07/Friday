# Multi-stage build for optimized production image
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /tmp

# Copy requirements and build wheels
COPY veritas-ai/requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /tmp/wheels -r requirements.txt


# Final production stage
FROM python:3.11-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 appuser

WORKDIR /app/veritas-ai

# Copy pre-built wheels from builder
COPY --from=builder /tmp/wheels /tmp/wheels

# Install wheels with constraints
COPY veritas-ai/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --no-index --find-links=/tmp/wheels -r /tmp/requirements.txt && \
    rm -rf /tmp/wheels /tmp/requirements.txt

# Copy application code
COPY --chown=appuser:appuser veritas-ai /app/veritas-ai

# Switch to non-root user
USER appuser

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
