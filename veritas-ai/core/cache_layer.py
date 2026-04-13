import json
import hashlib
from typing import Optional
from models.schemas import QueryResponse

class ResponseCache:
    """
    Subsystems level intelligence cache mapping previous execution chains securely natively.
    Bypasses costly graph generations for identical logic bounds reliably.
    """
    def __init__(self):
        # We use a pure memory dict here, but in production this scales to Redis smoothly.
        self._cache = {}

    def _generate_hash(self, query: str) -> str:
        """ Generate deterministic SHA-256 cache identifiers exactly representing the string limit. """
        clean_query = query.lower().strip()
        return hashlib.sha256(clean_query.encode('utf-8')).hexdigest()

    def get(self, query: str) -> Optional[QueryResponse]:
        """ Inspect local bounds dynamically for cache hits. """
        query_hash = self._generate_hash(query)
        if query_hash in self._cache:
            return self._cache[query_hash]
        return None

    def set(self, query: str, payload: QueryResponse) -> None:
        """ Save a resolved response into pure bounds perfectly limiting subsequent requests. """
        query_hash = self._generate_hash(query)
        self._cache[query_hash] = payload

# Global cache singleton natively
query_cache = ResponseCache()
