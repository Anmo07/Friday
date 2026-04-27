"""
Smart Multi-Layer Cache — Phases 6-8

Layer 1: Query Cache     — hash(query) → full response
Layer 2: Agent Cache     — hash(agent_name:input) → agent output
Layer 3: Embedding Cache — hash(query) → embedding vector results
Layer 4: Session Cache   — last 5 interactions per session

TTL Strategy:
  - news queries   → 5 min
  - general queries → 15 min
  - agent outputs   → 30 min
"""

import hashlib
import json
import logging
import re
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from models.schemas import QueryResponse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# TTL classification
# ---------------------------------------------------------------------------

NEWS_PATTERNS = re.compile(
    r"(news|latest|today|breaking|current|recent|update|headlines|happening)",
    re.IGNORECASE,
)


def _ttl_for_query(query: str) -> int:
    """Return TTL in seconds based on query type."""
    if NEWS_PATTERNS.search(query):
        return 300  # 5 minutes for news
    return 900  # 15 minutes for general


# ---------------------------------------------------------------------------
# In-memory LRU cache with TTL
# ---------------------------------------------------------------------------


@dataclass
class CacheEntry:
    value: Any
    expires_at: float
    created_at: float = field(default_factory=time.time)

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at


class LRUTTLCache:
    """Thread-safe in-memory LRU cache with per-entry TTL."""

    def __init__(self, max_size: int = 512):
        self._store: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            self._misses += 1
            return None
        if entry.is_expired:
            del self._store[key]
            self._misses += 1
            return None
        self._store.move_to_end(key)
        self._hits += 1
        return entry.value

    def set(self, key: str, value: Any, ttl: int = 900) -> None:
        if key in self._store:
            del self._store[key]
        elif len(self._store) >= self._max_size:
            self._store.popitem(last=False)
        self._store[key] = CacheEntry(
            value=value,
            expires_at=time.time() + ttl,
        )

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()

    @property
    def stats(self) -> Dict[str, Any]:
        total = self._hits + self._misses
        return {
            "size": len(self._store),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / total, 3) if total > 0 else 0,
        }


# ---------------------------------------------------------------------------
# Session cache
# ---------------------------------------------------------------------------

class SessionCache:
    """Stores the last N interactions per session."""

    def __init__(self, max_per_session: int = 5):
        self._sessions: Dict[str, List[Dict[str, Any]]] = {}
        self._max = max_per_session

    def add(self, session_id: str, query: str, response: Dict[str, Any]) -> None:
        if session_id not in self._sessions:
            self._sessions[session_id] = []
        self._sessions[session_id].append({
            "query": query,
            "response": response,
            "timestamp": time.time(),
        })
        # Keep only last N
        self._sessions[session_id] = self._sessions[session_id][-self._max:]

    def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        return self._sessions.get(session_id, [])

    def clear(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)


# ---------------------------------------------------------------------------
# Smart Cache Controller
# ---------------------------------------------------------------------------

def _hash_key(prefix: str, value: str) -> str:
    normalized = " ".join(value.lower().strip().split())
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    return f"sc:{prefix}:{digest}"


class SmartCache:
    """
    Unified multi-layer cache controller.
    Checks all layers before allowing pipeline execution.
    """

    def __init__(self):
        self.query_cache = LRUTTLCache(max_size=256)
        self.agent_cache = LRUTTLCache(max_size=512)
        self.embedding_cache = LRUTTLCache(max_size=128)
        self.session_cache = SessionCache(max_per_session=5)

    # ----- Query Cache -----

    async def get_query(self, query: str) -> Optional[QueryResponse]:
        key = _hash_key("query", query)
        cached = self.query_cache.get(key)
        if cached:
            logger.debug(f"Smart cache HIT (query): {query[:50]}")
            return QueryResponse(**json.loads(cached))
        return None

    async def set_query(self, query: str, response: QueryResponse) -> None:
        key = _hash_key("query", query)
        ttl = _ttl_for_query(query)
        serialized = json.dumps(response.model_dump(), default=str)
        self.query_cache.set(key, serialized, ttl)

    # ----- Agent Cache -----

    async def get_agent(self, agent_name: str, input_hash: str) -> Optional[str]:
        key = _hash_key("agent", f"{agent_name}:{input_hash}")
        return self.agent_cache.get(key)

    async def set_agent(self, agent_name: str, input_hash: str, output: str, ttl: int = 1800) -> None:
        key = _hash_key("agent", f"{agent_name}:{input_hash}")
        self.agent_cache.set(key, output, ttl)

    # ----- Embedding Cache -----

    async def get_embedding(self, query: str) -> Optional[List[Dict]]:
        key = _hash_key("emb", query)
        cached = self.embedding_cache.get(key)
        if cached:
            return json.loads(cached)
        return None

    async def set_embedding(self, query: str, results: List[Dict], ttl: int = 3600) -> None:
        key = _hash_key("emb", query)
        self.embedding_cache.set(key, json.dumps(results, default=str), ttl)

    # ----- Session Cache -----

    def add_session_entry(self, session_id: str, query: str, response: Dict[str, Any]) -> None:
        self.session_cache.add(session_id, query, response)

    def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        return self.session_cache.get_history(session_id)

    # ----- Stats -----

    def get_stats(self) -> Dict[str, Any]:
        return {
            "query_cache": self.query_cache.stats,
            "agent_cache": self.agent_cache.stats,
            "embedding_cache": self.embedding_cache.stats,
        }


# Module-level singleton
smart_cache = SmartCache()
