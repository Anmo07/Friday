import asyncio
import time
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
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
    StreamAuthorizationResponse,
)
from pipelines.multi_agent_pipeline import (
    run_multi_agent_pipeline,
    run_fast_pipeline,
)


router = APIRouter(prefix=settings.API_V1_PREFIX)
limiter = Limiter(key_func=get_remote_address)





class PerformanceMetrics(BaseModel):
    latency_ms: float
    cache_hit: bool
    routing_decision: str


async def _resolve_query(clean_query: str, owner_email: str = "public") -> tuple[QueryResponse, PerformanceMetrics]:
    """
    Unified query resolution using the Smart Routing layer.
    Phase 2 & 3: Handles caching and routing internally.
    """
    start_time = time.time()
    
    # Use the unified route_and_execute logic
    response, routing_result = await route_and_execute(
        query=clean_query,
        fast_pipeline_fn=run_fast_pipeline,
        full_pipeline_fn=run_multi_agent_pipeline
    )
    
    latency_ms = (time.time() - start_time) * 1000
    cache_hit = (routing_result.decision == RoutingDecision.CACHE_HIT)
    
    # Log result asynchronously
    await asyncio.to_thread(log_query_result, response, owner_email)
    
    # Update metrics and return
    return response, PerformanceMetrics(
        latency_ms=latency_ms,
        cache_hit=cache_hit,
        routing_decision=routing_result.decision.value
    )



@router.post("/query", response_model=QueryResponse)
@limiter.limit("5/minute")
async def query_endpoint(request: Request, body: QueryRequest):
    response, _ = await _resolve_query(body.query)
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
    response, _ = await _resolve_query(body.query, current_user["owner"])
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
        user = get_current_user(api_key, request)
        owner_email = user["owner"]
    items = await asyncio.to_thread(fetch_recent_history, limit, owner_email)
    return HistoryResponse(status="success", items=items)


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
