FROM python:3.9-slim

# Install system dependencies required by Playwright and other C++ extensions
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    build-essential \
    libffi-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Ensure pip is up to date
RUN pip install --upgrade pip

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies natively
RUN pip install --no-cache-dir -r requirements.txt

# Download Playwright OS dependencies and browser binaries natively
RUN playwright install-deps
RUN playwright install chromium

# Copy the entire backend application context
COPY . .

# Expose the Uvicorn FastAPI port
EXPOSE 8000

# Start the event-driven WebSocket and API server dynamically
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
