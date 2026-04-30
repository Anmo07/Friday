# --- BUILD STAGE ---
FROM python:3.11-slim-bookworm AS builder

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    build-essential \
    libffi-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
# Force CPU-only torch in container to avoid downloading CUDA runtimes.
RUN pip install --user --upgrade pip && \
    pip install --user --index-url https://download.pytorch.org/whl/cpu "torch==2.11.0+cpu" && \
    pip install --user -r requirements.txt

# --- FINAL STAGE ---
FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/home/friday/.local/bin:$PATH

# Create a non-privileged user for security
RUN groupadd -g 1001 friday && \
    useradd -u 1001 -g friday -m -s /bin/bash friday

# System dependencies for audio and ffmpeg
RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    curl \
    libportaudio2 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /home/friday/.local
RUN chown -R friday:friday /home/friday/.local

# Create necessary directories and set permissions
RUN mkdir -p /app/data /app/chroma_db /app/logs && \
    chown -R friday:friday /app

USER friday


# Copy application source
COPY --chown=friday:friday . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Production server execution using uvicorn workers
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--limit-concurrency", "100"]
