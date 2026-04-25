"""Deep pipeline: comprehensive analysis with extended validation."""
import asyncio
import logging
from typing import Dict, Optional, Callable

from app.agents.retrieval import retrieval_agent
from app.agents.validation import validation_agent
from app.agents.response import response_agent

logger = logging.getLogger(__name__)


async def deep_pipeline(
    query: str, progress_callback: Optional[Callable] = None
) -> Dict:
    """
    Run deep analysis pipeline.
    First retrieves sources, then validates with source context.
    More thorough than fast_pipeline — retrieval informs validation.
    """
    if progress_callback:
        await progress_callback("processing", "Starting deep analysis...")

    # Phase 1: Retrieve sources first
    if progress_callback:
        await progress_callback("data_collection", "Collecting sources...")
    retrieval_data = await retrieval_agent(query)

    # Phase 2: Validate with source context (validation uses retrieval results)
    if progress_callback:
        await progress_callback("verification", "Validating claims...")
    validation_data = await validation_agent(query, sources=retrieval_data)

    # Phase 3: Build response
    if progress_callback:
        await progress_callback("generating", "Building comprehensive response...")
    response = await response_agent(query, [retrieval_data, validation_data])

    if progress_callback:
        await progress_callback("complete", "Deep analysis complete")

    return response
