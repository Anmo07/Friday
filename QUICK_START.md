# 🚀 Friday Quick Start Guide (macOS)

Friday is now optimized as a native macOS Menu Bar assistant. 

### 1. Installation & Setup

```bash
# 1. Clone the project
git clone https://github.com/Anmo07/Friday.git
cd Friday

# 2. Setup Virtual Environment
python -m venv venv
source venv/bin/activate

# 3. Install in editable mode (adds the 'friday' command)
pip install -e .
```

### 2. Launching Friday

Simply run the command below:
```bash
friday
```

A **Liquid Glass Orb** will appear in your top Menu Bar. You can now minimize your terminal.

### 3. Interaction & Triggers

Friday is built for hands-free activation:
- **Voice Trigger**: Say **"Hey Friday"** or simply **"Friday"**.
- **Acoustic Trigger**: **Clap Twice** in rapid succession.
- **Siri-Style UI**: A glowing orb will pop out in the bottom-right of your screen when Friday is listening or thinking.

## 🔧 Model Configuration Options

During setup, you can choose how Friday accesses AI models:

### 1. Local Ollama (Recommended for Privacy)
- Runs completely on your computer
- No internet required after initial model download
- First run will download models automatically (may take a few minutes)

### 2. Ollama Cloud
- Uses Ollama's cloud infrastructure
- Requires Ollama Cloud account and API key
- Faster initial setup, models hosted remotely

### 3. Hugging Face Fallback
- Uses Hugging Face models as backup
- Good option if you have limited local resources
- May require internet connectivity

## 📋 Prerequisites

Before running Friday, ensure you have:

### For Docker Method:
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Docker Compose)
- At least 4GB RAM available
- 5GB+ free disk space

### For Manual Method:
- Python 3.9+
- Node.js 16+
- Redis, Neo4j, ChromaDB, and Ollama installed separately
- More technical knowledge required

## 🛠️ Common Tasks

### Viewing Logs
```bash
# See real-time logs
./setup-friday.sh logs

# Or with Docker directly
docker compose logs -f
```

### Stopping Friday
```bash
./setup-friday.sh stop

# Or with Docker directly
docker compose down
```

### Restarting Friday
```bash
./setup-friday.sh restart

# Or with Docker directly
docker compose down && docker compose up --build
```

### Checking Status
```bash
./setup-friday.sh status
```

## ❓ Troubleshooting

### "Address already in use" error
This means another service is using ports 3000, 8001, 7474, 7687, 8200, 6379, or 11434.
- Stop conflicting services
- Or change ports in docker-compose.yml

### Models not downloading
- Check your internet connection
- For Docker: Ensure the ollama container has internet access
- Try pulling models manually: `docker exec friday-ollama ollama pull mistral`

### Frontend not loading
- Wait 30-60 seconds for all services to start
- Check if backend is healthy: `curl http://localhost:8001/api/v1/health`
- Clear browser cache or try incognito mode

### CLI "Module Not Found" or Stalling
If you see text recognized but no response, or get module errors:
- Ensure you are using the virtual environment: `source .venv/bin/activate`
- Run the CLI via the venv: `./.venv/bin/friday`
- If using global `friday`, reinstall it in your current environment: `pip install -e .`
- Check for multiple Python versions (e.g. 3.14 vs 3.12). Friday is tested on 3.10-3.13.

### Getting Help
- Check logs: `./setup-friday.sh logs`
- Review the [README.md](README.md) for detailed documentation
- Visit the [GitHub repository](https://github.com/Anmo07/Friday) for issues and discussions

## 🎯 First-Time Usage Tips

1. **Initial model download** may take 5-15 minutes depending on your internet speed
2. **First verification** might be slower as models load into memory
3. **Subsequent requests** will be much faster (typically under 2 seconds)
4. **Try sample queries** like:
   - "Is the Earth flat?"
   - "Did humans land on the moon?"
   - "What is the capital of France?"

## 🔒 Privacy Notes

- With **Local Ollama**: All processing happens on your computer, no data leaves your machine
- With **Ollama Cloud**: Prompts are sent to Ollama's servers (review their privacy policy)
- Friday itself doesn't collect or store your queries beyond temporary processing

---

**Enjoy using Friday - your AI-powered truth verification assistant!**