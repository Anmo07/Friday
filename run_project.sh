#!/bin/bash
# -------------------------------------------------------------
# Project Setup & Execution Script for Veritas AI
# -------------------------------------------------------------
# NOTE: The clean rewrite lives in the app/ module.
#       New entry point: uvicorn app.main:app
#       Docker Compose handles everything automatically.

echo "--- 🚀 Setting up Veritas AI ---"

# Navigate to the correct directory where docker-compose.yml lives
cd veritas-ai || { echo "❌ Directory veritas-ai not found."; exit 1; }

# The project uses a complex stack (Neo4j, Chroma, Redis, Ollama, FastAPI, Next.js).
# The most reliable way to run it locally is via Docker Compose as per README.md.

if command -v docker &> /dev/null; then
    echo "📦 Docker found. Building and starting all services via Docker Compose..."
    
    # Build and start services in the background (-d)
    docker compose up --build -d
    
    if [ $? -eq 0 ]; then
        echo -e "\n=================================================="
        echo "🎉 SUCCESS: Veritas AI is starting up!"
        echo "=================================================="
        echo "Backend API should be available at: http://localhost:8001/api/v1/health"
        echo "Frontend UI should be available at: http://localhost:3000"
        echo "Neo4j Browser should be available at: http://localhost:7474"
        echo "Use 'docker compose logs -f' in the veritas-ai directory to follow logs."
        echo "=================================================="
    else
        echo "🚨 FAILURE: Docker compose failed."
        exit 1
    fi
else
    echo "❌ Docker is not installed. This project requires Docker to easily run its dependencies (Neo4j, Redis, Chroma, Ollama)."
    echo "Please install Docker and try again."
    exit 1
fi
