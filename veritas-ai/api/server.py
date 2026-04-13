from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from models.schemas import QueryResponse
from pipelines.multi_agent_pipeline import run_multi_agent_pipeline

router = APIRouter(prefix="/api/v1")

class QueryRequest(BaseModel):
    query: str

@router.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    """
    Primary endpoint for Veritas AI.
    Accepts a user query, processes it through the multi-agent pipeline,
    and returns a strictly formatted JSON response.
    """
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query string cannot be empty.")
        
    response = await run_multi_agent_pipeline(request.query)
    return response

@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "veritas-ai"}
