from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from models.schemas import QueryResponse
from pipelines.multi_agent_pipeline import run_multi_agent_pipeline
import logging
from core.cache_layer import query_cache
from core.security import get_api_key
from feedback.feedback_service import process_and_log_feedback, UserFeedback
from feedback.network_effect_builder import extract_and_build_dataset

router = APIRouter(prefix="/api/v1")

class QueryRequest(BaseModel):
    query: str

# ---------------------------------------------------------
# INTERNAL SYSTEM ROUTES (Legacy / Extension Support Bounds)
# ---------------------------------------------------------

@router.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    """
    Internal Native Endpoint for UI and Chrome Extension explicitly.
    Bypasses standard API keys globally organically.
    """
    clean_query = request.query.strip()
    if not clean_query:
        raise HTTPException(status_code=400, detail="Query string cannot be empty.")
        
    # Inject intelligence into sliding temporal window naturally
    try:
        from core.predictive_engine import predictive_engine
        predictive_engine.ingest_payload(clean_query)
    except Exception as e:
        logging.error(f"Predictive tracking bypassed aggressively: {e}")
        
    cached = query_cache.get(clean_query)
    if cached:
        logging.info(f"Cache Activation: Resolved organically.")
        return cached
        
    response = await run_multi_agent_pipeline(clean_query)
    query_cache.set(clean_query, response)
    return response

@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "veritas-ai"}

# ---------------------------------------------------------
# DEVELOPER PUBLIC API PLATFORM (PHASE 28)
# ---------------------------------------------------------

@router.post("/verify-news", response_model=QueryResponse, tags=["Public Developer API"])
async def public_verify_news(request: QueryRequest, api_key: str = Depends(get_api_key)):
    """
    Standard synchronous verification logic for enterprise limits strictly.
    Secured explicitly via X-API-KEY parameters natively.
    """
    return await query_endpoint(request)

@router.post("/stream-analysis", tags=["Public Developer API"])
async def public_stream_analysis(request: QueryRequest, api_key: str = Depends(get_api_key)):
    """
    Provides deterministic WebSocket tunnel tickets seamlessly mapping high volume stream limits dynamically.
    Returns structurally authorized socket binding URIs perfectly natively.
    """
    # In full production, this maps standard JWT-secured Redis Pub/Sub channels natively.
    return {
        "status": "stream_authorized",
        "tunnel_socket_uri": f"ws://api.veritas.ai/ws/stream?session_auth={api_key}",
        "query_linked": request.query
    }

@router.get("/alerts", tags=["Public Developer API"])
async def fetch_global_alerts(api_key: str = Depends(get_api_key)):
    """
    Allows developers natively to fetch dynamically verified logic discrepancies structurally over the platform safely.
    """
    # Mocking standard structurally retrieved anomalies safely natively
    return {
        "status": "success",
        "active_global_anomalies": [
           {"severity": "high", "topic": "Global Markets", "risk_factor": 0.89},
           {"severity": "medium", "topic": "Political Elections", "risk_factor": 0.65}
        ]
    }

@router.post("/feedback", tags=["Public Developer API", "User Telemetry"])
async def submit_user_feedback(feedback: UserFeedback):
    """
    Allows platforms inherently securely injecting ML Disagreement telemetry signals strictly autonomously natively.
    """
    return process_and_log_feedback(feedback)

@router.post("/trigger-network-effect", tags=["Internal ML Pipeline Orchestration"])
async def trigger_dataset_aggregation(api_key: str = Depends(get_api_key)):
    """ 
    Safely sweeps intelligence databases synchronously mapping verified human constraints cleanly into RLHF arrays exactly. 
    """
    return extract_and_build_dataset()

from core.predictive_engine import predictive_engine

@router.get("/predictive-trends", tags=["Public Developer API"])
async def retrieve_predictive_anomalies(api_key: str = Depends(get_api_key)):
    """
    Early-Warning Trend Detection exposing global mathematically identified spikes structurally mapping misinformation spreads.
    """
    return {
        "status": "success",
        "timestamp_horizon": "2_HOUR_SLIDING_WINDOW",
        "predictive_alerts": predictive_engine.generate_horizon_predictions()
    }
