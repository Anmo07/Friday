"""
Legacy fast pipeline — now delegates to the adaptive pipeline (L1 mode).

Kept for backward compatibility with any code that imports fast_pipeline.
"""

from models.schemas import QueryResponse
from pipelines.adaptive_pipeline import run_adaptive_pipeline


async def fast_pipeline(query: str) -> QueryResponse:
    """Fast path: delegates to adaptive pipeline at L1 (Fast) depth."""
    return await run_adaptive_pipeline(query, force_deep=False)
