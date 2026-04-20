import asyncio
from typing import Any

from core.router import router as query_router
from models.schemas import QueryResponse
from agents.veritas_agents import retrieve_sources, validate_claim, generate_response

async def fast_pipeline(query: str) -> QueryResponse:
    """Fast path: minimal retrieval and validation.

    Retrieves up to 5 sources, validates the claim using the ValidationEngine,
    and returns a concise response. Designed to stay under 2 seconds.
    """
    # Step 1: retrieve sources (stub or real RAG)
    sources_data = await retrieve_sources(query)
    # Step 2: validate claim
    validation = await validate_claim(sources_data)
    # Step 3: generate response dict
    response_dict = await generate_response(query, validation)
    # Convert to QueryResponse model
    return QueryResponse(**response_dict)
