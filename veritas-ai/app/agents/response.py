"""Response agent: builds final QueryResponse from agent results."""
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


async def response_agent(query: str, results: List[Dict]) -> Dict:
    """Build final response from retrieval + validation results. Implemented in Task 2."""
    raise NotImplementedError("Implemented in Task 2")
