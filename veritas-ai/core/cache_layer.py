import hashlib
from typing import Optional

from cachetools import TTLCache

from config.settings import settings
from models.schemas import QueryResponse


class ResponseCache:
    """
    Subsystems level intelligence cache mapping previous execution chains securely natively.
    Bypasses costly graph generations for identical logic bounds reliably.
    """
    def __init__(self):
        self._cache = TTLCache(
            maxsize=settings.CACHE_MAX_ENTRIES,
            ttl=settings.CACHE_TTL_SECONDS,
        )

    def normalize_query(self, query: str) -> str:
        return " ".join(query.lower().strip().split())

    def _generate_hash(self, query: str) -> str:
        """ Generate deterministic SHA-256 cache identifiers exactly representing the string limit. """
        clean_query = self.normalize_query(query)
        return hashlib.sha256(clean_query.encode('utf-8')).hexdigest()

    def get(self, query: str) -> Optional[QueryResponse]:
        """ Inspect local bounds dynamically for cache hits. """
        query_hash = self._generate_hash(query)
        return self._cache.get(query_hash)

    def set(self, query: str, payload: QueryResponse) -> None:
        """ Save a resolved response into pure bounds perfectly limiting subsequent requests. """
        query_hash = self._generate_hash(query)
        self._cache[query_hash] = payload

# Global cache singleton natively
query_cache = ResponseCache()
