# Use Debian Bookworm for Playwright compatibility
FROM python:3.9-slim-bookworm AS builder

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    build-essential \
    libffi-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --upgrade pip

COPY requirements.txt .
RUN pip install --user -r requirements.txt


FROM python:3.9-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

# System dependencies for audio, build tools, and Playwright browser deps
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    curl \
    libportaudio2 \
    portaudio19-dev \
    espeak-ng \
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
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

WORKDIR /app

RUN python -m playwright install chromium

COPY . .

RUN mkdir -p /app/data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Preload models at startup and run server
CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:11434/api/tags', timeout=5)" 2>/dev/null || echo "Ollama not ready, continuing..." && \
    uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4 --limit-concurrency 100
