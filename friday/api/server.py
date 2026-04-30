import asyncio
import time
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address

from config.settings import settings
from core.alert_engine import get_recent_alerts
from core.history_store import fetch_recent_history, log_query_result
from core.predictive_engine import predictive_engine
from core.redis_cache import redis_cache
from core.router import (
    RoutingDecision,
    route_and_execute,
    router as query_router,
)
from core.security import get_api_key, get_current_user, api_key_header
from feedback.feedback_service import UserFeedback, process_and_log_feedback
from feedback.network_effect_builder import extract_and_build_dataset
from models.schemas import (
    AlertsResponse,
    FeedbackResponse,
    HealthResponse,
    HistoryResponse,
    PredictiveTrendsResponse,
    QueryResponse,
    QueryRequest,
    StreamAuthorizationResponse,
)
from pipelines.fast_pipeline import fast_pipeline
from pipelines.deep_pipeline import deep_pipeline
from voice.voice_manager import voice_manager
from voice.voice_manager import voice_manager
from voice.tts_engine import tts_engine, VOICE_PROFILES


router = APIRouter(prefix=settings.API_V1_PREFIX)
limiter = Limiter(key_func=get_remote_address)





class PerformanceMetrics(BaseModel):
    latency_ms: float
    cache_hit: bool
    routing_decision: str


async def _resolve_query(clean_query: str, deep: bool = False, owner_email: str = "public") -> tuple[QueryResponse, PerformanceMetrics]:
    """
    Unified query resolution using fast and deep pipelines.
    """
    start_time = time.time()
    
    if deep:
        response = await deep_pipeline(clean_query)
        decision = "DEEP"
    else:
        response = await fast_pipeline(clean_query)
        decision = "FAST"
    
    latency_ms = (time.time() - start_time) * 1000
    cache_hit = False
    
    # Log result asynchronously
    await asyncio.to_thread(log_query_result, response, owner_email)
    
    # Update metrics and return
    return response, PerformanceMetrics(
        latency_ms=latency_ms,
        cache_hit=cache_hit,
        routing_decision=decision
    )



@router.post("/query", response_model=QueryResponse)
@limiter.limit("5/minute")
async def query_endpoint(request: Request, body: QueryRequest):
    response, _ = await _resolve_query(body.query, body.deep)
    return response


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        service="veritas-ai",
        version="0.2.0",
    )


@router.post(
    "/verify-news", response_model=QueryResponse, tags=["Public Developer API"]
)
@limiter.limit("100/minute")
async def public_verify_news(
    request: Request, body: QueryRequest, current_user: dict = Depends(get_current_user)
):
    response, _ = await _resolve_query(body.query, body.deep, current_user["owner"])
    return response


@router.post(
    "/stream-analysis",
    response_model=StreamAuthorizationResponse,
    tags=["Public Developer API"],
)
@limiter.limit("20/minute")
async def public_stream_analysis(
    request: Request, body: QueryRequest, api_key: str = Depends(get_api_key)
):
    separator = "&" if "?" in settings.PUBLIC_WS_BASE_URL else "?"
    return StreamAuthorizationResponse(
        status="stream_authorized",
        tunnel_socket_uri=f"{settings.PUBLIC_WS_BASE_URL}{separator}session_auth={api_key}",
        query_linked=body.query,
    )


@router.get("/alerts", response_model=AlertsResponse, tags=["Public Developer API"])
@limiter.limit("60/minute")
async def fetch_global_alerts(request: Request, current_user: dict = Depends(get_current_user)):
    return AlertsResponse(
        status="success",
        active_global_anomalies=get_recent_alerts(),
    )
@router.get("/history", response_model=HistoryResponse, tags=["Internal UI"])
@limiter.limit("60/minute")
async def fetch_query_history(request: Request, limit: int = Query(default=25, ge=1, le=100), api_key: Optional[str] = Depends(api_key_header)):
    owner_email = "public"
    if api_key:
        user = await get_current_user(api_key)
        owner_email = user["owner"]
    items = await asyncio.to_thread(fetch_recent_history, limit, owner_email)
    return HistoryResponse(status="success", items=items)


class VoiceProfileRequest(BaseModel):
    voice_id: str

@router.post("/voice/set", tags=["Voice"])
async def set_voice_profile(body: VoiceProfileRequest):
    # Set the current voice in tts_engine and persist to redis
    tts_engine.voice = VOICE_PROFILES.get(body.voice_id, tts_engine.voice)
    await redis_cache.set("voice:current", body.voice_id, expire=86400)
    return {"status": "success", "voice": tts_engine.voice}

@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    tags=["Public Developer API", "User Telemetry"],
)
@limiter.limit("10/minute")
async def submit_user_feedback(request: Request, feedback: UserFeedback, api_key: Optional[str] = Depends(api_key_header)):
    owner_email = "public"
    if api_key:
        user = get_current_user(api_key, request)
        owner_email = user["owner"]
    result = await asyncio.to_thread(process_and_log_feedback, feedback, owner_email)
    return FeedbackResponse(**result)


@router.post(
    "/trigger-network-effect",
    response_model=FeedbackResponse,
    tags=["Internal ML Pipeline Orchestration"],
)
@limiter.limit("5/minute")
async def trigger_dataset_aggregation(request: Request, current_user: dict = Depends(get_current_user)):
    result = await asyncio.to_thread(extract_and_build_dataset)
    return FeedbackResponse(
        status=result["status"],
        message=result.get("message") or result.get("output_target"),
    )


@router.get(
    "/predictive-trends",
    response_model=PredictiveTrendsResponse,
    tags=["Public Developer API"],
)
@limiter.limit("30/minute")
async def retrieve_predictive_anomalies(request: Request, current_user: dict = Depends(get_current_user)):
    return PredictiveTrendsResponse(
        status="success",
        timestamp_horizon="2_HOUR_SLIDING_WINDOW",
        predictive_alerts=predictive_engine.generate_horizon_predictions(),
    )


@router.get("/metrics")
@limiter.limit("60/minute")
async def get_performance_metrics(request: Request):
    return {
        "status": "success",
        "router_metrics": query_router.get_metrics(),
        "cache_stats": await redis_cache.get_stats(),
    }


@router.post("/cache/clear")
@limiter.limit("5/minute")
async def clear_cache(request: Request, prefix: Optional[str] = None):
    await redis_cache.clear(prefix)
    return {
        "status": "success",
        "message": f"Cache cleared for prefix: {prefix or 'all'}",
    }


@router.websocket("/ws/query")
async def websocket_query(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            query = data.get("query", "")
            deep = data.get("deep", False)
            
            # Send initial progress state
            await websocket.send_json({"stage": "Analyzing...", "status": "running"})
            
            # Run the query resolution
            response, metrics = await _resolve_query(query, deep)
            
            # Send final response
            await websocket.send_json({
                "stage": "Result ready",
                "status": "complete",
                "response": response.model_dump(),
                "metrics": metrics.model_dump()
            })
    except WebSocketDisconnect:
        print("Analysis WebSocket disconnected")

@router.websocket("/ws/voice")
async def websocket_voice(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # We expect audio bytes from the client
            audio_bytes = await websocket.receive_bytes()
            
            # Send immediate feedback that we're processing
            await websocket.send_json({"stage": "Listening...", "status": "running"})
            
            # 1. Transcribe audio to text
            query_text = await voice_manager.transcribe_audio(audio_bytes)
            if not query_text:
                await websocket.send_json({
                    "stage": "Result ready", 
                    "status": "error", 
                    "error": "Could not hear audio."
                })
                continue
                
            await websocket.send_json({"stage": f"Transcribed: {query_text}", "status": "running"})
            
            # 2. Resolve query quickly (fast pipeline)
            # Default to fast mode for voice to keep response time < 2s
            response, _ = await _resolve_query(query_text, deep=False)
            
            # 3. Generate speech from summary
            await websocket.send_json({"stage": "Generating voice...", "status": "running"})
            speech_audio_bytes = await tts_engine.generate_speech(response.summary)
            
            # 4. Return results and audio back to client
            # We send JSON with the text response, and audio bytes separately or encoded
            # For simplicity, returning just audio bytes, or you can send a JSON payload 
            # with base64 encoded audio. Let's send the text summary, then the audio binary.
            await websocket.send_json({
                "stage": "Result ready",
                "status": "complete",
                "response": response.model_dump()
            })
            await websocket.send_bytes(speech_audio_bytes)
            
    except WebSocketDisconnect:
        print("Voice WebSocket disconnected")
