"""Unified caching layer: local TTLCache + Redis backend."""
import hashlib
import json
import logging
import asyncio
from typing import Optional, Any, Dict

from cachetools import TTLCache

from app.core.config import settings

logger = logging.getLogger(__name__)


class UnifiedCache:
    """
    Single cache interface replacing redis_cache, cache_layer, and router cache.

    Two-tier caching:
    - L1: Local TTLCache (fast, in-process, bounded)
    - L2: Redis (shared across workers, persistent)

    Graceful degradation: if Redis is unavailable, falls back to L1 only.
    """

    def __init__(
        self,
        local_maxsize: int = settings.CACHE_MAX_ENTRIES,
        local_ttl: int = 300,
    ):
        self._local: TTLCache = TTLCache(maxsize=local_maxsize, ttl=local_ttl)
        self._redis = None  # redis.asyncio.Redis instance
        self._redis_available: bool = False
        self._default_ttl: int = settings.CACHE_TTL_SECONDS
        self._stats: Dict[str, int] = {"hits_local": 0, "hits_redis": 0, "misses": 0, "sets": 0}

    @staticmethod
    def _make_key(query: str) -> str:
        """Generate consistent cache key from query."""
        normalized = query.strip().lower()
        return f"veritas:query:{hashlib.sha256(normalized.encode()).hexdigest()[:16]}"

    async def connect(self, redis_url: str = settings.redis_url, timeout: float = 2.0):
        """
        Initialize Redis connection with timeout.
        Falls back to local-only cache if Redis is unavailable.
        """
        try:
            import redis.asyncio as aioredis

            self._redis = aioredis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=timeout,
                socket_timeout=timeout,
            )
            # Test connection
            await asyncio.wait_for(self._redis.ping(), timeout=timeout)
            self._redis_available = True
            logger.info(f"Redis cache connected: {redis_url}")
        except Exception as e:
            logger.warning(f"Redis unavailable, using local cache only: {e}")
            self._redis_available = False
            self._redis = None

    async def get(self, query: str) -> Optional[Dict]:
        """
        Get cached response. Checks L1 (local) first, then L2 (Redis).
        Returns None on cache miss.
        """
        key = self._make_key(query)

        # L1: Local cache
        local_result = self._local.get(key)
        if local_result is not None:
            self._stats["hits_local"] += 1
            logger.debug(f"Cache L1 hit: {key}")
            return local_result

        # L2: Redis cache
        if self._redis_available and self._redis:
            try:
                raw = await self._redis.get(key)
                if raw is not None:
                    result = json.loads(raw)
                    # Promote to L1
                    self._local[key] = result
                    self._stats["hits_redis"] += 1
                    logger.debug(f"Cache L2 hit: {key}")
                    return result
            except Exception as e:
                logger.warning(f"Redis get failed: {e}")

        self._stats["misses"] += 1
        return None

    async def set(self, query: str, response: Dict, ttl: Optional[int] = None):
        """
        Cache a response in both L1 and L2.
        """
        key = self._make_key(query)
        ttl = ttl or self._default_ttl
        self._stats["sets"] += 1

        # L1: Always set local
        self._local[key] = response

        # L2: Set Redis if available
        if self._redis_available and self._redis:
            try:
                raw = json.dumps(response, default=str)
                await self._redis.setex(key, ttl, raw)
            except Exception as e:
                logger.warning(f"Redis set failed: {e}")

    async def delete(self, query: str):
        """Delete a cached entry from both tiers."""
        key = self._make_key(query)
        self._local.pop(key, None)
        if self._redis_available and self._redis:
            try:
                await self._redis.delete(key)
            except Exception as e:
                logger.warning(f"Redis delete failed: {e}")

    async def clear(self, prefix: str = "veritas:"):
        """Clear all cached entries."""
        self._local.clear()
        if self._redis_available and self._redis:
            try:
                cursor = 0
                while True:
                    cursor, keys = await self._redis.scan(
                        cursor, match=f"{prefix}*", count=100
                    )
                    if keys:
                        await self._redis.delete(*keys)
                    if cursor == 0:
                        break
                logger.info("Redis cache cleared")
            except Exception as e:
                logger.warning(f"Redis clear failed: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Return cache statistics."""
        total_hits = self._stats["hits_local"] + self._stats["hits_redis"]
        total_requests = total_hits + self._stats["misses"]
        return {
            **self._stats,
            "total_hits": total_hits,
            "total_requests": total_requests,
            "hit_rate": total_hits / max(total_requests, 1),
            "redis_available": self._redis_available,
            "local_size": len(self._local),
        }

    async def close(self):
        """Close Redis connection."""
        if self._redis:
            try:
                await self._redis.close()
            except Exception:
                pass
            self._redis = None
            self._redis_available = False
        self._local.clear()
        logger.info("Cache closed")


# Module-level singleton
cache = UnifiedCache()
