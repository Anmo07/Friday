"""
Legacy deep pipeline — now delegates to the adaptive pipeline (L3 mode).

Kept for backward compatibility with any code that imports deep_pipeline.
"""

from models.schemas import QueryResponse
from pipelines.adaptive_pipeline import run_adaptive_pipeline


async def deep_pipeline(query: str) -> QueryResponse:
    """Full deep analysis — delegates to adaptive pipeline at L3 (Deep) depth."""
    return await run_adaptive_pipeline(query, force_deep=True)
