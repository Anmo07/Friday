FROM python:3.9-slim

# System dependencies for Playwright, audio libs, and build tools
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    build-essential \
    libffi-dev \
    libssl-dev \
    curl \
    libportaudio2 \
    portaudio19-dev \
    espeak-ng \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --upgrade pip

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright browsers
RUN playwright install-deps
RUN playwright install chromium

# Copy full application
COPY . .

# Create data directory for SQLite DBs, audit logs, notes
RUN mkdir -p /app/data

# Expose FastAPI
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Start the event-driven WebSocket and API server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
