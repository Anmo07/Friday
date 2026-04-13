# Project Friday: Veritas AI 
**Autonomous Real-Time News Intelligence & Fake News Detection Platform**

---

## 🚀 LATEST UPGRADES & CHANGES (Phases 1-9 Completed)

We successfully mapped and deployed the complete 9-phase autonomous multi-agent architecture. The system is fully structurally integrated as a microservice framework leveraging local Large Language Models.

1. **Async Fast-RAG Memory (Phase 2 & 9):**
   - Established local document persistence utilizing `ChromaDB` alongside `langchain-ollama` local embeddings.
   - Refactored synchronous document insertion into thread-safe asynchronous chunks (`batch_size=50`) resolving token spikes on primary node CPUs.
2. **CrewAI Autonomous Agents (Phase 3 & 8):**
   - **Intelligence Planner:** Autonomously maps data collection structures.
   - **Data Executor:** Resolves extraction instructions blindly.
   - **Source Verification Officer:** Flags Domain `.go` / `.edu`, scales credibility via strict explicit rulesets.
   - **Fact Checker:** RAG-enabled memory verification agent looking for localized explicit contradictions.
   - **Misinformation Analyst:** Evaluates raw emotional tensors and sequences probability metrics.
   - **Chief Intelligence Critic:** Enforces a multi-pass validation loop structurally binding all loose hallucinations back to strict objectivity.
3. **Data Scraper Array (Phase 4):**
   - Headless scraping integrated recursively leveraging **Playwright** spiders.
   - Automated RSS fetchers via **Feedparser** & REST API mappings directly hitting **GNews.io** endpoints securely.
4. **NLP Math Verification (Phase 6):**
   - Replaced pure textual NLP inference requests with a localized HuggingFace Transformer `mrm8488/bert-tiny-finetuned-fake-news-detection` avoiding hallucinations mathematically via `transformers.pipeline`.
5. **Real-time ASGI Edge-Sockets & Optimization (Phase 7 & 9):**
   - Implemented `TTLCache` natively mapping `QueryRequest` hashes up to 15-minutes dynamically.
   - Enabled bi-directional WebSocket logic mapped to `ws/stream` allowing decoupling of massive CrewAI sequential queues from failing HTTP gateway timeouts.
   - Deployed LangChain native `SQLiteCache` trapping repetitive local inference cycles reliably out of the backend database mapping.

---

## 🧠 CORE SYSTEM ARCHITECTURE

`Veritas AI` acts as the foundational sub-project inside **Friday**. It is engineered as a highly decoupled Multi-Agent RAG processing pipeline intended to intake raw user queries and autonomously research, verify, fact-check, and construct strictly structured final JSON intelligence payloads. 

### Technology Stack
- **API Framework:** Async FastAPI / Uvicorn (HTTP & WebSockets).
- **Agent Orchestrator:** CrewAI (mapped locally inside Langchain boundaries).
- **Core Intelligence:** Local LLMs via `langchain-ollama` (Zero reliance on OpenAI APIs necessary).
- **Vector Storage:** Persistent Local Chroma DB instances. 
- **Classification ML:** HuggingFace `torch` pipelines executing RoBERTa-based logic models for emotion/fake-news detection natively.
- **Web Navigation:** Playwright synchronous DOM chunk reading (`sync_playwright`).

### Data Flow Execution Lifecycle
1. **Intake:** The query is routed through either an HTTP POST via `/api/v1/query` or via standard bi-directional WebSockets (`/ws/stream`). Cache boundaries check for repetition natively here using TTL metrics.
2. **Planning & Extraction:** The Planner maps tasks which the Data Executor leverages the Playwright/Requests/Feedparser tools to accomplish.
3. **Scrubbing & Scoring:** The Verification Agent scrubs domains and issues metrics (e.g. `credibility_score = 0.95`). The Fact Checker loops claims against `Chroma` RAG pipelines resolving truth structures. 
4. **Linguistic Scan:** The Misinformation Analyst evaluates textual SPAs autonomously executing Tensor classifications for explicit Fake News probability markers natively. 
5. **Review:** The Critic Agent strictly enforces alignment, neutralizing contradictions and formatting text. 
6. **Emission:** LangChain Pydantic Parsers rigorously assert standard schema shapes to the intelligence report and return raw JSON data. 

### Pydantic Output Structuring (Strict Baseline)
All pipelines deterministically assert the following JSON Object resolution back to the caller without exception:
```json
{
  "query": "string",
  "summary": "string",
  "facts": ["string"],
  "sources": [
    {
      "url": "string",
      "credibility_score": "number",
      "type": "official | media | social"
    }
  ],
  "contradictions": ["string"],
  "fake_probability": "number",
  "confidence_score": "number",
  "timestamp": "string"
}
```
