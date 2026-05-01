import asyncio
import logging
import time
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from app.core.config import settings
from app.core.cache import cache

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1")


def _get_pipeline(request: Request):
    pipeline = getattr(request.app.state, "pipeline", None)
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    return pipeline


def _require_api_key(request: Request) -> str:
    if settings.ALLOW_ANONYMOUS_QUERY_ENDPOINT:
        return "anonymous"
    api_key = request.headers.get("X-API-KEY")
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")
    from core.security import validate_api_key
    validate_api_key(api_key)
    return api_key


def _get_owner_email(api_key: str, request: Request) -> str:
    try:
        from core.security import get_current_user

        user = get_current_user(api_key, request)
        return user.get("owner", "public")
    except:
        return "public"


async def _resolve_query(
    request: Request, query: str, deep: bool = False, owner_email: str = "public"
) -> dict:
    cached = await cache.get(query)
    if cached is not None:
        cached["_cached"] = True
        return cached
    
    start = time.monotonic()
    pipeline = _get_pipeline(request)
    
    # Tiered TTL strategy
    ttl = settings.CACHE_TTL_SECONDS
    query_lower = query.lower()
    if any(word in query_lower for word in ["news", "today", "current", "latest"]):
        ttl = 3600  # 1 hour for news
    elif any(word in query_lower for word in ["science", "physics", "biology", "math"]):
        ttl = 86400  # 24 hours for science
    elif any(word in query_lower for word in ["history", "was", "happened", "ancient"]):
        ttl = 604800  # 7 days for historical facts

    try:
        # Enforce request timeout per endpoint logic
        response = await asyncio.wait_for(
            pipeline.run(query), 
            timeout=settings.PIPELINE_TIMEOUT_SECONDS
        )
    except asyncio.TimeoutError:
        logger.error(f"Pipeline timeout for query: {query}")
        response = {"response": "Analysis timed out. Try a simpler query.", "error": True, "code": "TIMEOUT"}
    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        response = {"response": str(e), "error": True}
        
    response["latency_ms"] = round((time.monotonic() - start) * 1000, 1)
    await cache.set(query, response, ttl=ttl)
    
    try:
        from core.history_store import log_query_result
        from models.schemas import QueryResponse

        payload = QueryResponse(
            response=response.get("response", ""),
            truth_score=response.get("truth_score"),
            sources=response.get("context_used", []),
        )
        asyncio.create_task(asyncio.to_thread(log_query_result, payload, owner_email))
    except:
        pass
    return response


@router.get("/health")
async def health():
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
    api_key = _require_api_key(request)
    owner_email = _get_owner_email(api_key, request)
    body = await request.json()
    query = body.get("query", "").strip()
    deep = body.get("deep", False)
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")
    return await _resolve_query(request, query, deep=deep, owner_email=owner_email)


@router.post("/verify-news")
async def verify_news(request: Request):
    api_key = _require_api_key(request)
    owner_email = _get_owner_email(api_key, request)
    body = await request.json()
    query = body.get("claim", body.get("query", "")).strip()
    deep = body.get("deep", False)
    if not query:
        raise HTTPException(status_code=400, detail="Claim required")
    return await _resolve_query(request, query, deep=deep, owner_email=owner_email)


@router.post("/stream")
async def stream_query(request: Request):
    api_key = _require_api_key(request)
    body = await request.json()
    query = body.get("query", "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query required")
    pipeline = _get_pipeline(request)
    return StreamingResponse(
        pipeline.stream_run(query, voice_mode=bool(body.get("voice_mode", False))),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/voice/stream")
async def voice_stream_endpoint(request: Request):
    body = await request.json()
    text = body.get("text", "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text required")
    from app.voice.tts_service import tts_service

    return StreamingResponse(tts_service.stream_audio(text), media_type="audio/wav")


@router.get("/history")
async def get_history(request: Request, limit: int = 50):
    api_key = request.headers.get("X-API-KEY")
    owner_email = _get_owner_email(api_key, request) if api_key else "public"
    try:
        from core.history_store import fetch_recent_history

        history = await asyncio.to_thread(fetch_recent_history, limit, owner_email)
        return {"history": history, "count": len(history)}
    except Exception as e:
        return {"history": [], "count": 0, "error": str(e)}


@router.post("/feedback")
async def submit_feedback(request: Request):
    try:
        body = await request.json()
        from feedback.feedback_service import UserFeedback, process_and_log_feedback

        api_key = request.headers.get("X-API-KEY")
        owner_email = _get_owner_email(api_key, request) if api_key else "public"
        feedback = UserFeedback(**body)
        result = await asyncio.to_thread(
            process_and_log_feedback, feedback, owner_email
        )
        return {"status": "received", "message": "Feedback recorded", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/security/rotate-key")
async def rotate_key(request: Request):
    api_key = _require_api_key(request)
    from core.security import generate_new_api_key, DEVELOPER_DB
    
    # Get current user info to preserve tier and email
    current_user = DEVELOPER_DB.get(api_key, {"tier": "free", "owner": "unknown"})
    new_key = generate_new_api_key(tier=current_user["tier"], email=current_user["owner"])
    
    # Optional: Deactivate old key after rotation (standard security practice)
    # DEVELOPER_DB.pop(api_key, None) 
    
    return {"status": "success", "new_key": new_key, "message": "Save this key; it will not be shown again."}


@router.get("/metrics")
async def get_metrics():
    return {"cache": cache.get_stats(), "version": "2.0.0"}


@router.post("/cache/clear")
async def clear_cache():
    await cache.clear()
    return {"status": "cleared"}
