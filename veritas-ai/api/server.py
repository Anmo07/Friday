from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from models.schemas import QueryResponse
from pipelines.multi_agent_pipeline import run_multi_agent_pipeline
from cachetools import TTLCache
import logging

router = APIRouter(prefix="/api/v1")

# Fast in-memory cache to prevent identical query spikes mapped to 15 minute TTL parameters
endpoint_query_cache = TTLCache(maxsize=100, ttl=900)

class QueryRequest(BaseModel):
    query: str

@router.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    """
    Primary endpoint for Veritas AI.
    Accepts a user query, processes it through the multi-agent pipeline,
    and returns a strictly formatted JSON response.
    """
    clean_query = request.query.strip()
    if not clean_query:
        raise HTTPException(status_code=400, detail="Query string cannot be empty.")
        
    if clean_query in endpoint_query_cache:
        logging.info(f"Phase 9 Fast-Track Cache Activation: Resolved [{clean_query}] natively.")
        return endpoint_query_cache[clean_query]
        
    response = await run_multi_agent_pipeline(clean_query)
    
    endpoint_query_cache[clean_query] = response
    return response

@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "veritas-ai"}
