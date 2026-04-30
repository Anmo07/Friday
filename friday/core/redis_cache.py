import asyncio
import hashlib
import json
import logging
from datetime import datetime
from typing import Optional, Any, Dict, List

import redis.asyncio as redis
from redis.asyncio import Redis

from config.settings import settings
from models.schemas import QueryResponse


logger = logging.getLogger(__name__)


class RedisCache:
    _instance: Optional["RedisCache"] = None
    _redis: Optional[Redis] = None
    _local_cache: Dict[str, Any] = {}
    _lock: asyncio.Lock = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._lock = asyncio.Lock()
        return cls._instance

    async def connect(self) -> None:
        if self._redis is None:
            async with self._lock:
                if self._redis is None:
                    try:
                        redis_url = (
                            f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}"
                        )
                        self._redis = redis.from_url(
                            redis_url,
                            encoding="utf-8",
                            decode_responses=True,
                            socket_connect_timeout=5,
                            socket_timeout=5,
                        )
                        await self._redis.ping()
                        logger.info("Connected to Redis successfully")
                    except Exception as e:
                        logger.warning(
                            f"Redis connection failed, using local cache: {e}"
                        )
                        self._redis = None

    async def disconnect(self) -> None:
        if self._redis:
            await self._redis.close()
            self._redis = None

    def _normalize_query(self, query: str) -> str:
        return " ".join(query.lower().strip().split())

    def _generate_cache_key(self, query: str, prefix: str = "query") -> str:
        normalized = self._normalize_query(query)
        hash_key = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
        return f"veritas:{prefix}:{hash_key}"

    async def get(self, query: str, prefix: str = "query") -> Optional[QueryResponse]:
        cache_key = self._generate_cache_key(query, prefix)

        if cache_key in self._local_cache:
            cached_data = self._local_cache[cache_key]
            if cached_data:
                return QueryResponse(**json.loads(cached_data))

        if self._redis:
            try:
                cached_data = await self._redis.get(cache_key)
                if cached_data:
                    self._local_cache[cache_key] = cached_data
                    return QueryResponse(**json.loads(cached_data))
            except Exception as e:
                logger.warning(f"Redis get failed: {e}")

        return None

    async def set(
        self,
        query: str,
        response: QueryResponse,
        prefix: str = "query",
        ttl: Optional[int] = None,
    ) -> None:
        cache_key = self._generate_cache_key(query, prefix)
        ttl = ttl or settings.CACHE_TTL_SECONDS

        response_dict = response.model_dump()
        response_dict["timestamp"] = datetime.utcnow().isoformat() + "Z"
        serialized = json.dumps(response_dict, default=str)

        self._local_cache[cache_key] = serialized

        if self._redis:
            try:
                await self._redis.setex(cache_key, ttl, serialized)
            except Exception as e:
                logger.warning(f"Redis set failed: {e}")

    async def delete(self, query: str, prefix: str = "query") -> None:
        cache_key = self._generate_cache_key(query, prefix)

        self._local_cache.pop(cache_key, None)

        if self._redis:
            try:
                await self._redis.delete(cache_key)
            except Exception as e:
                logger.warning(f"Redis delete failed: {e}")

    async def clear(self, prefix: Optional[str] = None) -> None:
        if prefix:
            pattern = f"veritas:{prefix}:*"
        else:
            pattern = "veritas:*"

        keys_to_delete = [
            k
            for k in self._local_cache.keys()
            if k.startswith("veritas:") and (prefix is None or prefix in k)
        ]
        for key in keys_to_delete:
            self._local_cache.pop(key, None)

        if self._redis:
            try:
                cursor = 0
                while True:
                    cursor, keys = await self._redis.scan(
                        cursor, match=pattern, count=100
                    )
                    if keys:
                        await self._redis.delete(*keys)
                    if cursor == 0:
                        break
            except Exception as e:
                logger.warning(f"Redis clear failed: {e}")

    async def get_stats(self) -> Dict[str, Any]:
        stats = {
            "local_cache_size": len(self._local_cache),
            "redis_connected": self._redis is not None,
        }

        if self._redis:
            try:
                info = await self._redis.info("stats")
                stats["redis_stats"] = {
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0),
                    "total_commands_processed": info.get("total_commands_processed", 0),
                }
            except Exception:
                pass

        return stats


class VectorCache:
    _instance: Optional["VectorCache"] = None
    _redis: Optional[Redis] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def connect(self) -> None:
        if self._redis is None:
            try:
                redis_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}"
                self._redis = redis.from_url(
                    redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                )
                await self._redis.ping()
            except Exception:
                self._redis = None

    def _generate_embedding_key(self, query: str) -> str:
        normalized = " ".join(query.lower().strip().split())
        hash_key = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
        return f"veritas:embedding:{hash_key}"

    async def get_cached_results(self, query: str) -> Optional[List[Dict]]:
        if not self._redis:
            return None

        cache_key = self._generate_embedding_key(query)
        try:
            cached = await self._redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Vector cache get failed: {e}")
        return None

    async def cache_results(
        self, query: str, results: List[Dict], ttl: int = 3600
    ) -> None:
        if not self._redis:
            return

        cache_key = self._generate_embedding_key(query)
        try:
            await self._redis.setex(cache_key, ttl, json.dumps(results, default=str))
        except Exception as e:
            logger.warning(f"Vector cache set failed: {e}")


redis_cache = RedisCache()
vector_cache = VectorCache()


async def init_redis_cache() -> None:
    await redis_cache.connect()
    await vector_cache.connect()


async def close_redis_cache() -> None:
    await redis_cache.disconnect()
