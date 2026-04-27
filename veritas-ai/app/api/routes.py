"""REST API routes for Veritas AI."""
import asyncio
import logging
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.assistant import assistant_orchestrator
from app.core.cache import cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")


# ---- Auth Helpers ----

def _require_api_key(request: Request) -> str:
    """Extract and validate API key from request headers."""
    api_key = request.headers.get("X-API-KEY")
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")

    from core.security import validate_api_key
    validate_api_key(api_key)
    return api_key


def _get_owner_email(api_key: str, request: Request) -> str:
    """Resolve owner email from API key, falling back to 'public'."""
    try:
        from core.security import get_current_user
        user = get_current_user(api_key, request)
        return user.get("owner", "public")
    except Exception:
        return "public"


# ---- Query Resolution ----

async def _resolve_query(query: str, deep: bool = False, owner_email: str = "public") -> dict:
    """Run query through pipeline with caching."""
    intent = assistant_orchestrator.classify(query, deep_requested=deep)

    # Check cache first
    if intent.kind in {"chat", "verification"}:
        cached = await cache.get(query)
        if cached is not None:
            cached["_cached"] = True
            return cached

    start = time.monotonic()
    response = await assistant_orchestrator.execute(query, deep_requested=deep)

    response["latency_ms"] = round((time.monotonic() - start) * 1000, 1)

    # Cache result
    if intent.kind in {"chat", "verification"}:
        await cache.set(query, response)

    # Log to history (non-blocking)
    try:
        from core.history_store import log_query_result
        from models.schemas import QueryResponse

        payload = QueryResponse(**response)
        asyncio.create_task(asyncio.to_thread(log_query_result, payload, owner_email))
    except Exception:
        pass

    return response


# ---- Endpoints ----

@router.get("/health")
async def health():
    """Health check endpoint."""
    cache_stats = cache.get_stats()
    return {
        "status": "healthy",
        "version": "2.0.0",
        "cache": {
            "redis_available": cache_stats.get("redis_available", False),
            "hit_rate": round(cache_stats.get("hit_rate", 0), 4),
        },
    }


@router.post("/query")
async def query_endpoint(request: Request):
    """Direct query endpoint (no auth required)."""
    body = await request.json()
    query = body.get("query", "").strip()
    deep = body.get("deep", False)

    if not query:
        raise HTTPException(status_code=400, detail="Query is required")

    response = await _resolve_query(query, deep=deep)
    return response


@router.post("/verify-news")
async def verify_news(request: Request):
    """Public API for news verification (auth required)."""
    api_key = _require_api_key(request)
    owner_email = _get_owner_email(api_key, request)

    body = await request.json()
    query = body.get("claim", body.get("query", "")).strip()
    deep = body.get("deep", False)

    if not query:
        raise HTTPException(status_code=400, detail="Claim/query is required")

    response = await _resolve_query(query, deep=deep, owner_email=owner_email)
    return response


@router.post("/stream-analysis")
async def stream_analysis(request: Request):
    """Get WebSocket stream authorization URL (auth required)."""
    api_key = _require_api_key(request)

    body = await request.json()
    query = body.get("query", "").strip()

    separator = "&" if "?" in settings.PUBLIC_WS_BASE_URL else "?"
    return {
        "status": "stream_authorized",
        "tunnel_socket_uri": f"{settings.PUBLIC_WS_BASE_URL}{separator}session_auth={api_key}",
        "query_linked": query,
    }


@router.get("/history")
async def get_history(request: Request, limit: int = 50):
    """Fetch query history."""
    api_key = request.headers.get("X-API-KEY")
    owner_email = _get_owner_email(api_key, request) if api_key else "public"

    try:
        from core.history_store import fetch_recent_history
        history = await asyncio.to_thread(fetch_recent_history, limit, owner_email)
        return {"history": history, "count": len(history)}
    except Exception as e:
        logger.error(f"History fetch failed: {e}")
        return {"history": [], "count": 0, "error": str(e)}


@router.post("/feedback")
async def submit_feedback(request: Request):
    """Submit user feedback (data collection only).
    
    TODO:
    - dataset builder
    - training pipeline
    """
    try:
        body = await request.json()
        from feedback.feedback_service import UserFeedback, process_and_log_feedback

        api_key = request.headers.get("X-API-KEY")
        owner_email = _get_owner_email(api_key, request) if api_key else "public"

        feedback = UserFeedback(**body)
        result = await asyncio.to_thread(process_and_log_feedback, feedback, owner_email)
        return {"status": "received", "message": "Feedback recorded", "result": result}
    except Exception as e:
        logger.error(f"Feedback submission failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger-network-effect")
async def trigger_network_effect(request: Request):
    """Trigger dataset aggregation (auth required)."""
    _require_api_key(request)

    try:
        from feedback.network_effect_builder import extract_and_build_dataset
        result = await asyncio.to_thread(extract_and_build_dataset)
        return {
            "status": result.get("status", "success"),
            "message": result.get("message") or result.get("output_target"),
            "entries_parsed": result.get("entries_parsed", 0),
        }
    except Exception as e:
        logger.error(f"Network effect trigger failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts")
async def get_alerts(request: Request):
    """Fetch active alerts (auth required)."""
    _require_api_key(request)

    try:
        from core.alert_engine import get_recent_alerts
        alerts = get_recent_alerts()
        return {"alerts": alerts}
    except Exception as e:
        logger.error(f"Alerts fetch failed: {e}")
        return {"alerts": [], "error": str(e)}


@router.get("/predictive-trends")
async def get_trends(request: Request):
    """Fetch predictive trends (auth required)."""
    _require_api_key(request)

    try:
        from core.predictive_engine import predictive_engine
        trends = predictive_engine.generate_horizon_predictions()
        return {"trends": trends}
    except Exception as e:
        logger.error(f"Trends fetch failed: {e}")
        return {"trends": [], "error": str(e)}


@router.post("/voice/set")
async def set_voice_profile(request: Request):
    """Set TTS voice profile."""
    body = await request.json()
    profile = body.get("voice", "friday")
    from app.voice.tts import set_voice
    set_voice(profile)
    return {"status": "ok", "voice": profile}


@router.get("/metrics")
async def get_metrics():
    """Get system metrics."""
    cache_stats = cache.get_stats()
    return {
        "cache": cache_stats,
        "version": "2.0.0",
    }


@router.post("/cache/clear")
async def clear_cache():
    """Clear all caches."""
    await cache.clear()
    return {"status": "cleared"}
