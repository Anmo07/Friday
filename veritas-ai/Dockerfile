# Use Debian Bookworm for Playwright compatibility
FROM python:3.9-slim-bookworm

# System dependencies for audio, build tools, and Playwright browser deps
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
    # Playwright Chromium deps (Bookworm-compatible)
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

WORKDIR /app

RUN pip install --upgrade pip

# Install main Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install CrewAI separately with --no-deps (avoids langchain version conflict)
RUN pip install --no-cache-dir --no-deps crewai==0.1.32

# Install Playwright Chromium browser binary
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

# Start the API server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
