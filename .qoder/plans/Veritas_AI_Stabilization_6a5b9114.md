# Veritas AI System Stabilization Plan

## Current State Summary

The system has **2 critical runtime blockers**, **3 redundant cache layers**, **blocking synchronous calls**, **10-60s startup time**, a **stub retrieval agent**, and a **WebSocket endpoint mismatch** in Docker config. The deep pipeline crashes immediately due to a missing `VeritasAgents` class.

All work targets: `/Users/anmol/Downloads/Developer/Friday/veritas-ai/`

---

## Task 1: Project Structure Refactoring (Phase 1)

Create clean `app/` module structure inside `veritas-ai/`, migrating and consolidating existing code:

**Target layout:**
```
veritas-ai/
  app/
    __init__.py
    main.py              # from main.py (simplified startup)
    core/
      __init__.py
      router.py          # from core/router.py (simplified)
      config.py          # from config/settings.py
      cache.py           # UNIFIED cache (merge redis_cache + cache_layer + router cache)
    pipeline/
      __init__.py
      fast_pipeline.py   # from pipelines/fast_pipeline.py (rewritten with asyncio.gather)
      deep_pipeline.py   # from pipelines/deep_pipeline.py (rewritten, no CrewAI)
    agents/
      __init__.py
      retrieval.py       # from agents/veritas_agents.retrieve_sources (made functional)
      validation.py      # from core/validation_engine + truth_engine + firewall (consolidated)
      response.py        # from pipelines/response_builder.py (simplified)
    voice/
      __init__.py
      listener.py        # NEW: continuous mic listener with wake detection
      stt.py             # from voice/voice_manager.py (faster-whisper)
      tts.py             # from voice/tts_engine.py (non-blocking)
      emotion.py         # NEW: basic emotion detection from text
    api/
      __init__.py
      routes.py          # from api/server.py (cleaned, unified)
      websocket.py       # from api/websockets.py (streaming)
```

**Files to remove/deprecate** (old modules replaced by app/):
- `agents/query_agent.py` (never called)
- `pipelines/ingestion_pipeline.py` (never wired)
- `memory/knowledge_graph.py` (never imported)
- `core/cache_layer.py` (merged into `app/core/cache.py`)
- `core/validation_engine.py` (merged into `app/agents/validation.py`)

**Approach**: Create `app/` as the new entry point. Update `main.py` at project root to import from `app.main`. Old directories remain temporarily but are no longer imported.

---

## Task 2: Fix Agent Orchestration (Phase 2)

**Problem**: `VeritasAgents` class missing, agents run sequentially via CrewAI blocking calls.

**Solution**: Replace CrewAI-based orchestration with direct async functions:

```python
# app/agents/retrieval.py
async def retrieval_agent(query: str) -> dict:
    # Use Ollama directly via langchain, no CrewAI
    # Return sources dict with credibility scores

# app/agents/validation.py  
async def validation_agent(query: str, sources: dict = None) -> dict:
    # Run truth_engine.compute_truth_score
    # Run firewall logic
    # Return validation result

# app/agents/response.py
async def response_agent(query: str, results: list) -> QueryResponse:
    # Build final response from retrieval + validation results
```

**Pipeline rewrite** (`app/pipeline/fast_pipeline.py`):
```python
async def fast_pipeline(query: str) -> QueryResponse:
    results = await asyncio.gather(
        retrieval_agent(query),
        validation_agent(query)
    )
    return await response_agent(query, results)
```

**Key**: Remove all `asyncio.to_thread(crew.kickoff)` calls. Remove CrewAI dependency entirely.

---

## Task 3: Router (Fast vs Deep) (Phase 3)

**Simplify** `core/router.py` (currently 181 LOC with regex classifier):

```python
# app/core/router.py
from enum import Enum

class RouteDecision(str, Enum):
    FAST = "fast"
    DEEP = "deep"

def route(query: str) -> RouteDecision:
    if len(query.split()) < 10 or len(query) < 50:
        return RouteDecision.FAST
    trigger_words = {"compare", "analyze", "investigate", "explain why", "deep"}
    if any(w in query.lower() for w in trigger_words):
        return RouteDecision.DEEP
    return RouteDecision.FAST
```

Remove metrics tracking, caching within router (cache is handled separately).

---

## Task 4: Unified Redis Caching (Phase 4)

**Problem**: 3 overlapping caches with different TTLs, keys, and invalidation.

**Solution** (`app/core/cache.py`): Single unified cache with Redis primary + local fallback:

```python
class UnifiedCache:
    def __init__(self):
        self._local = TTLCache(maxsize=512, ttl=300)
        self._redis: Optional[redis.asyncio.Redis] = None
    
    async def get(self, query: str) -> Optional[dict]:
        key = self._make_key(query)
        # Check local first, then Redis
        
    async def set(self, query: str, response: dict, ttl: int = 900):
        # Write to both local and Redis
```

Replace all imports of `redis_cache`, `cache_layer`, `query_cache`, and router's TTLCache with `UnifiedCache`.

---

## Task 5: Fix Startup Time (Phase 5)

**Current**: 10-60s (model preload blocks, Redis wait, SQLite on import).

**Fix in `app/main.py`**:
1. Make model preload non-blocking (fire-and-forget background task)
2. Redis connection with 2s timeout, graceful fallback to local-only cache
3. Move SQLite init to explicit startup, not module import
4. Lazy-load heavy modules (transformers, torch) only when first needed

```python
async def _init_services():
    # Non-blocking: start all in parallel
    await asyncio.gather(
        _init_cache(),           # 2s timeout Redis
        _init_databases(),       # SQLite init
        return_exceptions=True
    )
    # Background model preload (don't block startup)
    asyncio.create_task(_preload_models_background())
```

**Target**: Startup < 3 seconds.

---

## Task 6: Voice Pipeline (Phase 6)

**Rewrite voice modules**:

- `app/voice/stt.py`: Faster-Whisper with lazy model loading, streaming transcription
- `app/voice/tts.py`: Edge-TTS (already async), non-blocking playback via `asyncio.create_task`
- `app/voice/emotion.py`: Simple keyword/sentiment-based emotion detection

```python
# app/voice/stt.py
async def transcribe(audio_bytes: bytes) -> str:
    model = _get_or_load_model()  # Lazy load
    return await asyncio.to_thread(_transcribe_sync, model, audio_bytes)
```

**Full pipeline**:
```python
async def voice_pipeline(audio: bytes) -> dict:
    text = await transcribe(audio)
    result = await fast_pipeline(text)
    audio_out = await speak(result["summary"])
    return {"text": result, "audio": audio_out}
```

---

## Task 7: Continuous Listener (Phase 7)

**New file** `app/voice/listener.py`:
- Background microphone listener using `sounddevice` or `pyaudio`
- Energy-based wake detection (clap) + optional keyword detection
- When triggered, pipes audio to voice pipeline
- WebSocket notification to frontend on activation

---

## Task 8: Latency Optimization (Phase 8)

- Replace all remaining `asyncio.to_thread()` with native async where possible
- Limit LLM calls to max 2 per query (1 retrieval, 1 response generation)
- Set RAG k=3 (already configured in docker-compose as `RETRIEVAL_K=3`)
- Remove synchronous response building chain (consensus, explainability, firewall) — make async or inline
- Add connection pooling for Redis

**Target**: Response start < 500ms, full response < 2s.

---

## Task 9: Streaming Response System (Phase 9)

**Rewrite** `app/api/websocket.py`:
- Send structured progress updates: `{"status": "listening|processing|generating|complete", "progress": 0-100}`
- Stream LLM tokens as generated (if Ollama supports streaming)
- Unified WebSocket endpoint at `/ws/stream`

**Frontend receives**: Real-time stage updates + partial results.

---

## Task 10: Error Handling and Stability (Phase 10)

Add to `app/main.py`:
- Global exception handler middleware (catch all, return JSON error)
- Per-endpoint timeout handling (configurable via config)
- Fallback responses when agents fail (graceful degradation)
- Circuit breaker pattern for external services (Ollama, Redis)

```python
@app.middleware("http")
async def error_handler(request, call_next):
    try:
        return await asyncio.wait_for(call_next(request), timeout=30)
    except asyncio.TimeoutError:
        return JSONResponse(status_code=504, content={"error": "Request timeout"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
```

---

## Task 11: Frontend Integration Fix (Phase 11)

**Fix API mismatches**:
1. Update `docker-compose.yml` line 58: `/ws/query` to `/ws/stream`
2. Update frontend `useWebSocket.ts` to handle new structured progress messages
3. Add streaming response rendering in `Dashboard.tsx`
4. Add voice activation button with WebSocket audio streaming
5. Fix fallback port (8000 vs 8001) in `frontend/services/api.ts`

---

## Task 12: Docker Fix (Phase 12)

1. Update backend `Dockerfile` to use `app/` as entry point
2. Fix `docker-compose.yml`: correct WS URLs, service names, port mappings
3. Remove `localhost` dependencies — use Docker service names
4. Optimize container startup: remove Playwright install (not needed for core), reduce worker count
5. Ensure `docker compose up --build` works end-to-end

---

## Execution Strategy

Tasks will be executed in dependency order:

1. **Task 1** (structure) -- foundation, must go first
2. **Tasks 2-4** (agents, router, cache) -- can partially parallelize
3. **Task 5** (startup) -- depends on cache being unified
4. **Tasks 6-7** (voice) -- independent of pipeline work
5. **Task 8** (latency) -- depends on new pipeline being in place
6. **Task 9** (streaming) -- depends on pipeline + websocket
7. **Task 10** (error handling) -- can run after core pipeline works
8. **Task 11** (frontend) -- depends on API being stable
9. **Task 12** (Docker) -- final integration, depends on everything

Each task will be verified before proceeding to the next.