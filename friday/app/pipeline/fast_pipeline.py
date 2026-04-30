"""Fast pipeline: parallel retrieval + validation, target < 2s."""
import asyncio
import logging
from typing import Dict, Optional, Callable

from app.agents.retrieval import retrieval_agent
from app.agents.validation import validation_agent
from app.agents.response import response_agent

logger = logging.getLogger(__name__)


async def fast_pipeline(
    query: str, progress_callback: Optional[Callable] = None
) -> Dict:
    """
    Run fast pipeline with parallel agents.
    Target latency: < 2 seconds.
    """
    if progress_callback:
        await progress_callback("processing", "Starting fast analysis...")

    # Run retrieval and validation in parallel
    results = await asyncio.gather(
        retrieval_agent(query),
        validation_agent(query),
        return_exceptions=True,
    )

    # Handle any agent failures gracefully
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.warning(f"Agent {i} failed: {result}")
            processed_results.append({})
        else:
            processed_results.append(result)

    if progress_callback:
        await progress_callback("generating", "Building response...")

    # Build final response
    response = await response_agent(query, processed_results)

    if progress_callback:
        await progress_callback("complete", "Analysis complete")

    return response
