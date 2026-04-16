import asyncio
import logging
import time
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from config.settings import settings
from core.alert_engine import get_recent_alerts
from core.cache_layer import query_cache
from core.history_store import fetch_recent_history, log_query_result
from core.predictive_engine import predictive_engine
from core.redis_cache import redis_cache
from core.router import router as query_router, RoutingDecision
from core.security import get_api_key
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
    PipelineError,
    run_multi_agent_pipeline,
    run_fast_pipeline,
)


router = APIRouter(prefix=settings.API_V1_PREFIX)


class QueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)

    @field_validator("query")
    @classmethod
    def clean_query(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("Query string cannot be empty.")
        return cleaned


class PerformanceMetrics(BaseModel):
    latency_ms: float
    cache_hit: bool
    routing_decision: str


async def _resolve_query(clean_query: str) -> tuple[QueryResponse, PerformanceMetrics]:
    start_time = time.time()

    try:
        predictive_engine.ingest_payload(clean_query)
    except Exception as exc:
        logging.warning("Predictive ingestion skipped: %s", exc)

    redis_cached = await redis_cache.get(clean_query)
    if redis_cached is not None:
        latency_ms = (time.time() - start_time) * 1000
        cached_response = redis_cached.model_copy(
            update={"timestamp": datetime.utcnow().isoformat() + "Z"}
        )
        await asyncio.to_thread(log_query_result, cached_response)
        return cached_response, PerformanceMetrics(
            latency_ms=latency_ms, cache_hit=True, routing_decision="redis_cache"
        )

    local_cached = query_cache.get(clean_query)
    if local_cached is not None:
        latency_ms = (time.time() - start_time) * 1000
        cached_response = local_cached.model_copy(
            update={"timestamp": datetime.utcnow().isoformat() + "Z"}
        )
        await asyncio.to_thread(log_query_result, cached_response)
        return cached_response, PerformanceMetrics(
            latency_ms=latency_ms, cache_hit=True, routing_decision="local_cache"
        )

    routing_result = query_router.route(clean_query)

    if routing_result.decision == RoutingDecision.FAST_PATH:
        try:
            response = await run_fast_pipeline(clean_query)
            await redis_cache.set(clean_query, response)
            latency_ms = (time.time() - start_time) * 1000
            await asyncio.to_thread(log_query_result, response)
            return response, PerformanceMetrics(
                latency_ms=latency_ms, cache_hit=False, routing_decision="fast_path"
            )
        except Exception as exc:
            logging.warning(
                "Fast pipeline failed, falling back to full pipeline: %s", exc
            )

    try:
        response = await run_multi_agent_pipeline(clean_query)
    except PipelineError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc

    await redis_cache.set(clean_query, response)
    query_cache.set(clean_query, response)
    await asyncio.to_thread(log_query_result, response)

    latency_ms = (time.time() - start_time) * 1000
    return response, PerformanceMetrics(
        latency_ms=latency_ms, cache_hit=False, routing_decision="full_pipeline"
    )


@router.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    response, _ = await _resolve_query(request.query)
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
async def public_verify_news(
    request: QueryRequest, api_key: str = Depends(get_api_key)
):
    response, _ = await _resolve_query(request.query)
    return response


@router.post(
    "/stream-analysis",
    response_model=StreamAuthorizationResponse,
    tags=["Public Developer API"],
)
async def public_stream_analysis(
    request: QueryRequest, api_key: str = Depends(get_api_key)
):
    separator = "&" if "?" in settings.PUBLIC_WS_BASE_URL else "?"
    return StreamAuthorizationResponse(
        status="stream_authorized",
        tunnel_socket_uri=f"{settings.PUBLIC_WS_BASE_URL}{separator}session_auth={api_key}",
        query_linked=request.query,
    )


@router.get("/alerts", response_model=AlertsResponse, tags=["Public Developer API"])
async def fetch_global_alerts(api_key: str = Depends(get_api_key)):
    return AlertsResponse(
        status="success",
        active_global_anomalies=get_recent_alerts(),
    )


@router.get("/history", response_model=HistoryResponse, tags=["Internal UI"])
async def fetch_query_history(limit: int = Query(default=25, ge=1, le=100)):
    items = await asyncio.to_thread(fetch_recent_history, limit)
    return HistoryResponse(status="success", items=items)


@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    tags=["Public Developer API", "User Telemetry"],
)
async def submit_user_feedback(feedback: UserFeedback):
    result = await asyncio.to_thread(process_and_log_feedback, feedback)
    return FeedbackResponse(**result)


@router.post(
    "/trigger-network-effect",
    response_model=FeedbackResponse,
    tags=["Internal ML Pipeline Orchestration"],
)
async def trigger_dataset_aggregation(api_key: str = Depends(get_api_key)):
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
async def retrieve_predictive_anomalies(api_key: str = Depends(get_api_key)):
    return PredictiveTrendsResponse(
        status="success",
        timestamp_horizon="2_HOUR_SLIDING_WINDOW",
        predictive_alerts=predictive_engine.generate_horizon_predictions(),
    )


@router.get("/metrics")
async def get_performance_metrics():
    return {
        "status": "success",
        "router_metrics": query_router.get_metrics(),
        "cache_stats": await redis_cache.get_stats(),
    }


@router.post("/cache/clear")
async def clear_cache(prefix: Optional[str] = None):
    await redis_cache.clear(prefix)
    return {
        "status": "success",
        "message": f"Cache cleared for prefix: {prefix or 'all'}",
    }
