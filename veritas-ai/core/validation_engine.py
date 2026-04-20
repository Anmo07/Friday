import asyncio
from typing import Dict, Any

from core.truth_engine import TruthEngine

# Singleton instance for reuse
_truth_engine = TruthEngine()

async def validate_claim(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a claim using the existing TruthEngine.

    This function runs the compute_truth_score method in a thread pool to avoid
    blocking the event loop. It returns the same structure as TruthEngine.compute_truth_score.
    """
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _truth_engine.compute_truth_score, data)
    return result
