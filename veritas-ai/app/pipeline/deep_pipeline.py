"""Deep pipeline: multi-perspective multi-agent analysis."""
import asyncio
import logging
from typing import Dict, Optional, Callable
from agents.multi_perspective.orchestrator import MultiPerspectiveOrchestrator
from models.schemas import QueryResponse

logger = logging.getLogger(__name__)

async def deep_pipeline(
    query: str, progress_callback: Optional[Callable] = None
) -> Dict:
    """
    Run deep analysis pipeline using the MultiPerspectiveOrchestrator.
    Implements Phase 1 and 2 of the system transformation.
    """
    if progress_callback:
        await progress_callback("processing", "Activating Control Room Mode...")

    orchestrator = MultiPerspectiveOrchestrator()
    
    # We can pass progress updates inside if we want, but for now just run it
    response_model: QueryResponse = await orchestrator.run(query)
    
    # Convert model to dict for the API
    response = response_model.dict()
    
    if progress_callback:
        await progress_callback("complete", "Multi-agent analysis complete, Boss.")

    return response
