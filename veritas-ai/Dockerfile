# Using official Microsoft Playwright image to bypass manual browser downloads and avoid network drops
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

# Install other system dependencies (audio, speech, build tools)
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    build-essential \
    curl \
    libportaudio2 \
    portaudio19-dev \
    espeak-ng \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --upgrade pip

# Install main Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install CrewAI separately with --no-deps (avoids langchain version conflict)
RUN pip install --no-cache-dir --no-deps crewai==0.1.32

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
