# --- BUILD STAGE ---
FROM python:3.11.9-slim-bookworm AS builder

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
# Note: For production CPU-only environments, consider:
# RUN pip install --user torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --user --upgrade pip && \
    pip install --user -r requirements.txt

# --- FINAL STAGE ---
FROM python:3.11.9-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/home/veritas/.local/bin:$PATH \
    PLAYWRIGHT_BROWSERS_PATH=/app/ms-playwright

# Create a non-privileged user for security
RUN groupadd -g 1001 veritas && \
    useradd -u 1001 -g veritas -m -s /bin/bash veritas

# System dependencies for audio, chromium, and ffmpeg
RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    curl \
    libportaudio2 \
    ffmpeg \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libxcomposite1 \
    libxrandr2 \
    libxdamage1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libgbm1 \
    libgtk-3-0 \
    libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /home/veritas/.local
RUN chown -R veritas:veritas /home/veritas/.local

# Create necessary directories and set permissions
RUN mkdir -p /app/data /app/chroma_db /app/logs /app/ms-playwright && \
    chown -R veritas:veritas /app

USER veritas

# Install Playwright browser (cached if requirements don't change)
# Optional: only needed if web scraping tools are enabled at runtime
RUN playwright install chromium

# Copy application source
COPY --chown=veritas:veritas . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Production server execution using uvicorn workers
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--limit-concurrency", "100"]
