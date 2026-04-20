import asyncio
from typing import Any

from models.schemas import QueryResponse
from pipelines.multi_agent_pipeline import run_multi_agent_pipeline

async def deep_pipeline(query: str) -> QueryResponse:
    """
    Full analysis – runs the original multi-agent pipeline in a background task.
    Returns the final QueryResponse when complete.
    """
    # Run the heavy pipeline in its own task so we don't block unnecessarily,
    # though since we await it here it will still take time for the user.
    # In a full streaming UX, this could yield progress events.
    task = asyncio.create_task(run_multi_agent_pipeline(query))
    return await task
