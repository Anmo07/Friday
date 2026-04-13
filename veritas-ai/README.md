# Veritas AI — AI-Powered Truth Engine

> **Real-time multi-agent intelligence for fake news detection, truth scoring, and misinformation analysis.**

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.9+-green.svg)
![Next.js](https://img.shields.io/badge/Next.js-14-black.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)

---

## What is Veritas AI?

Veritas AI is a production-grade, multi-agent intelligence platform that verifies news claims in real-time. It deploys six autonomous AI agents — powered by CrewAI, LangChain, and Ollama — that collaboratively fact-check, detect misinformation, and deliver explainable truth scores.

**Tagline:** *AI-Powered Truth Engine*

### Key Capabilities

| Capability | Technology |
|---|---|
| Multi-Agent Verification | CrewAI + LangChain |
| Fake News Detection | HuggingFace Transformers |
| Knowledge Graph | Neo4j |
| Vector Search (RAG) | ChromaDB |
| Predictive Trends | Custom Spike Detection |
| Real-Time Streaming | WebSockets + FastAPI |
| Voice Interface | Web Speech API (Siri-like) |
| Browser Extension | Chrome Manifest V3 |

---

## Architecture

```
User (Voice / Text / Extension)
         │
         ▼
   ┌─────────────┐
   │  Next.js UI  │  ← Landing / Dashboard / Timeline / Feedback / API Docs
   └──────┬──────┘
          │ WebSocket + REST
          ▼
   ┌─────────────┐
   │  FastAPI     │  ← API Gateway + Auth + Rate Limiting
   └──────┬──────┘
          │
    ┌─────┼─────────────────────┐
    ▼     ▼                     ▼
 CrewAI  Transformers       Predictive
 Agents  (Fake Detection)   Engine
    │
    ├─ Fact Checker Agent
    ├─ Misinformation Analyzer
    ├─ Consensus Builder
    ├─ Explainability Agent
    └─ Alert Engine
          │
    ┌─────┼─────┐
    ▼     ▼     ▼
  Neo4j  Chroma  SQLite
  (KG)   (RAG)   (Feedback)
```

---

## Quick Start

### Local Development

```bash
# Backend
cd veritas-ai
pip install -r requirements.txt
python main.py

# Frontend
cd frontend
npm install
npm run dev
```

### Docker (Production)

```bash
cd veritas-ai
docker compose up --build
```

### Chrome Extension

1. Open `chrome://extensions/`
2. Enable Developer Mode
3. Click "Load unpacked" → select `veritas-ai/extension/`
4. Right-click any text → "Verify Truth via Veritas AI"

---

## API Reference

All authenticated endpoints require the `X-API-KEY` header.

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/query` | No | Internal verification (UI/Extension) |
| POST | `/api/v1/verify-news` | Yes | Public developer verification |
| POST | `/api/v1/stream-analysis` | Yes | WebSocket session authorization |
| GET | `/api/v1/alerts` | Yes | Active global anomalies |
| GET | `/api/v1/predictive-trends` | Yes | Early-warning trend predictions |
| POST | `/api/v1/feedback` | No | Submit user feedback |
| GET | `/api/v1/health` | No | Service health check |

---

## Use Cases

### For Journalists
Verify claims before publication. Get source-backed truth scores with full explainability breakdowns.

### For Researchers
Access real-time misinformation trend data through the Predictive Intelligence API.

### For Developers
Integrate truth scoring into any application via our REST API with sub-2-second latency.

### For Organizations
Deploy enterprise-grade misinformation monitoring with custom alert thresholds and dedicated infrastructure.

---

## Tech Stack

- **Backend:** Python 3.9, FastAPI, Uvicorn
- **AI/ML:** CrewAI, LangChain, Ollama, HuggingFace Transformers
- **Databases:** Neo4j (Knowledge Graph), ChromaDB (Vector), SQLite (Feedback)
- **Frontend:** Next.js 14, TypeScript, Tailwind CSS
- **Infrastructure:** Docker, Kubernetes, GitHub Actions CI/CD
- **Observability:** Prometheus, Grafana, OpenTelemetry

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

<p align="center">
  <strong>Veritas AI</strong> — Verify Truth. Expose Lies.<br/>
  Built by <a href="https://github.com/anmol">@anmol</a>
</p>
