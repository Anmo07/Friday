#!/bin/bash
# Friday Setup Script - Simplified installation for non-technical users
# Supports Docker (recommended) and manual installation with flexible model options

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Friday AI Setup Wizard ===${NC}"
echo "This script will help you set up Friday - AI-Powered Truth Engine"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to prompt user
prompt_user() {
    local prompt="$1"
    local default="$2"
    read -p "$prompt [$default]: " input
    echo "${input:-$default}"
}

# Function to check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}Checking prerequisites...${NC}"
    
    # Check Docker
    if ! command_exists docker; then
        echo -e "${RED}Error: Docker is not installed.${NC}"
        echo "Please install Docker from https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    # Check Docker Compose (v2)
    if ! docker compose version >/dev/null 2>&1; then
        echo -e "${RED}Error: Docker Compose plugin is not available.${NC}"
        echo "Please ensure you have Docker Desktop or Docker Engine with Compose plugin."
        exit 1
    fi
    
    # Check git
    if ! command_exists git; then
        echo -e "${RED}Error: Git is not installed.${NC}"
        echo "Please install Git from https://git-scm.com/downloads"
        exit 1
    fi
    
    echo -e "${GREEN}✓ Prerequisites check passed${NC}"
}

# Function to display setup options
display_setup_options() {
    echo -e "\n${YELLOW}Select installation method:${NC}"
    echo "1) Docker (Recommended - easiest, isolates all dependencies)"
    echo "2) Manual (For developers who want more control)"
    echo ""
    
    local choice
    choice=$(prompt_user "Enter your choice" "1")
    
    case "$choice" in
        1) echo "docker" ;;
        2) echo "manual" ;;
        *) 
            echo -e "${RED}Invalid choice. Please select 1 or 2.${NC}"
            display_setup_options
            ;;
    esac
}

# Function to configure model options
configure_model_options() {
    echo -e "\n${YELLOW}Select model source:${NC}"
    echo "1) Local Ollama (Recommended - runs completely on your machine)"
    echo "2) Ollama Cloud (Requires Ollama Cloud account)"
    echo "3) Hugging Face (Fallback option)"
    echo ""
    
    local choice
    choice=$(prompt_user "Enter your choice" "1")
    
    case "$choice" in
        1) 
            echo "local_ollama"
            # Set default models for local
            echo "MODEL_NAME=mistral" > .env.model
            echo "FAST_MODEL=mistral" >> .env.model
            echo "ROUTER_MODEL=phi3" >> .env.model
            ;;
        2)
            echo "ollama_cloud"
            # Prompt for Ollama Cloud credentials
            local api_key
            api_key=$(prompt_user "Enter your Ollama Cloud API key" "")
            if [ -z "$api_key" ]; then
                echo -e "${RED}Ollama Cloud API key is required.${NC}"
                configure_model_options
            fi
            echo "OLLAMA_CLOUD_API_KEY=$api_key" > .env.model
            echo "OLLAMA_CLOUD_ENDPOINT=https://api.ollama.com" >> .env.model
            echo "MODEL_NAME=mistral" >> .env.model
            echo "FAST_MODEL=mistral" >> .env.model
            echo "ROUTER_MODEL=phi3" >> .env.model
            ;;
        3)
            echo "huggingface"
            echo "USE_HF_FALLBACK=true" > .env.model
            echo "HF_MODEL=sentence-transformers/all-MiniLM-L6-v2" >> .env.model
            ;;
        *) 
            echo -e "${RED}Invalid choice. Please select 1, 2, or 3.${NC}"
            configure_model_options
            ;;
    esac
}

# Function to setup Docker installation
setup_docker() {
    echo -e "\n${GREEN}Setting up Friday with Docker...${NC}"
    
    # Check if we're in the friday directory
    if [ ! -d "friday" ]; then
        echo -e "${RED}Error: Please run this script from the Friday project root directory.${NC}"
        exit 1
    fi
    
    # Configure model options
    MODEL_PROVIDER=$(configure_model_options)
    
    # Create .env file if it doesn't exist
    if [ ! -f "friday/.env" ]; then
        echo "Creating default .env file..."
        cp friday/.env.example friday/.env 2>/dev/null || echo "# Friday Environment Variables" > friday/.env
    fi
    
    # Add model configuration to .env
    if [ -f ".env.model" ]; then
        echo "" >> friday/.env
        echo "# Model Configuration (added by setup script)" >> friday/.env
        cat .env.model >> friday/.env
        rm .env.model
    fi
    
    # Start Docker services
    echo -e "\n${YELLOW}Starting Friday services...${NC}"
    cd friday
    
    echo "Building and starting containers..."
    docker compose up --build -d
    
    echo "Waiting for services to be ready..."
    # Wait for backend health check
    local max_attempts=30
    local attempt=1
    while [ $attempt -le $max_attempts ]; do
        if docker compose exec -T backend curl -fs http://localhost:8000/api/v1/health >/dev/null 2>&1; then
            break
        fi
        echo -n "."
        attempt=$((attempt + 1))
        sleep 2
    done
    
    if [ $attempt -gt $max_attempts ]; then
        echo -e "\n${RED}Error: Services did not become ready in time.${NC}"
        echo "Check logs with: docker compose logs -f"
        exit 1
    fi
    
    echo -e "\n${GREEN}✓ Friday is now running!${NC}"
    echo ""
    echo -e "${GREEN}Access Friday at:${NC}"
    echo "  Frontend: http://localhost:3000"
    echo "  Backend API: http://localhost:8001"
    echo "  API Docs: http://localhost:8001/docs"
    echo ""
    echo -e "${YELLOW}Useful commands:${NC}"
    echo "  View logs: docker compose logs -f"
    echo "  Stop Friday: ./setup-friday.sh stop"
    echo "  Restart Friday: ./setup-friday.sh restart"
    echo ""
}

# Function to setup manual installation
setup_manual() {
    echo -e "\n${GREEN}Setting up Friday manually...${NC}"
    echo -e "${YELLOW}Note: Manual installation requires more technical knowledge.${NC}"
    echo "Consider using Docker mode for easier setup."
    echo ""
    
    # Check for Python
    if ! command_exists python3; then
        echo -e "${RED}Error: Python 3.9+ is required.${NC}"
        exit 1
    fi
    
    # Check for Node.js
    if ! command_exists node; then
        echo -e "${RED}Error: Node.js is required.${NC}"
        exit 1
    fi
    
    # Configure model options
    MODEL_PROVIDER=$(configure_model_options)
    
    # Setup backend
    echo -e "\n${YELLOW}Setting up backend...${NC}"
    if [ ! -d "friday" ]; then
        echo -e "${RED}Error: friday directory not found.${NC}"
        exit 1
    fi
    
    cd friday
    
    # Create virtual environment
    if [ ! -d "venv" ]; then
        echo "Creating Python virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment and install dependencies
    echo "Installing Python dependencies..."
    source venv/bin/activate
    pip install -r requirements.txt
    
    # Create .env file
    if [ ! -f ".env" ]; then
        echo "Creating .env file..."
        cp .env.example .env 2>/dev/null || echo "# Friday Environment Variables" > .env
    fi
    
    # Add model configuration
    if [ -f "../.env.model" ]; then
        echo "" >> .env
        echo "# Model Configuration (added by setup script)" >> .env
        cat ../.env.model >> .env
        rm ../.env.model
    fi
    
    # Setup frontend
    echo -e "\n${YELLOW}Setting up frontend...${NC}"
    if [ ! -d "../frontend" ]; then
        echo -e "${RED}Error: frontend directory not found.${NC}"
        exit 1
    fi
    
    cd ../frontend
    if [ ! -d "node_modules" ]; then
        echo "Installing Node.js dependencies..."
        npm install
    fi
    
    echo -e "\n${GREEN}✓ Friday manual setup complete!${NC}"
    echo ""
    echo -e "${GREEN}To start Friday:${NC}"
    echo "  1. Start backend:"
    echo "     cd friday && source venv/bin/activate && python -m uvicorn app.main:app --host 0.0.0.0 --port 8001"
    echo "  2. In another terminal, start frontend:"
    echo "     cd frontend && npm run dev"
    echo ""
    echo -e "${YELLOW}Note: You'll need to manually start required services (Redis, Neo4j, ChromaDB, Ollama).${NC}"
    echo "Consider using Docker mode for automatic service management."
}

# Function to show status
show_status() {
    if [ -d "friday" ] && [ -f "friday/docker-compose.yml" ]; then
        cd friday
        if docker compose ps | grep -q "Up"; then
            echo -e "${GREEN}Friday is running (Docker mode)${NC}"
            docker compose ps
        else
            echo -e "${YELLOW}Friday is not running (Docker mode)${NC}"
        fi
    else
        echo -e "${YELLOW}Cannot determine Friday status${NC}"
    fi
}

# Function to stop Friday
stop_friday() {
    if [ -d "friday" ] && [ -f "friday/docker-compose.yml" ]; then
        echo -e "${YELLOW}Stopping Friday services...${NC}"
        cd friday
        docker compose down
        echo -e "${GREEN}Friday stopped.${NC}"
    else
        echo -e "${YELLOW}Cannot stop Friday - not in Docker mode or directory not found.${NC}"
    fi
}

# Main script logic
if [ $# -eq 0 ]; then
    # Interactive mode
    check_prerequisites
    
    INSTALL_METHOD=$(display_setup_options)
    
    case "$INSTALL_METHOD" in
        "docker")
            setup_docker
            ;;
        "manual")
            setup_manual
            ;;
    esac
    
else
    # Command line mode
    case "$1" in
        "start")
            check_prerequisites
            setup_docker
            ;;
        "stop")
            stop_friday
            ;;
        "restart")
            stop_friday
            setup_docker
            ;;
        "status")
            show_status
            ;;
        "help")
            echo -e "${GREEN}Friday Setup Script${NC}"
            echo "Usage: $0 [command]"
            echo ""
            echo "Commands:"
            echo "  (no args)  Interactive setup wizard"
            echo "  start      Start Friday with Docker (non-interactive)"
            echo "  stop       Stop Friday services"
            echo "  restart    Restart Friday services"
            echo "  status     Show Friday status"
            echo "  help       Show this help message"
            ;;
        *)
            echo -e "${RED}Unknown command: $1${NC}"
            echo "Use '$0 help' for usage information."
            exit 1
            ;;
    esac
fi

echo -e "${GREEN}Setup completed successfully!${NC}"