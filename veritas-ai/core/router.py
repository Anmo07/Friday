import hashlib
import re
import time
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Callable, Awaitable, Any

from cachetools import TTLCache
from config.settings import settings
from models.schemas import QueryResponse
from core.redis_cache import redis_cache

logger = logging.getLogger(__name__)

class QueryType(Enum):
    SIMPLE = "simple"
    FACTUAL = "factual"
    COMPLEX = "complex"

class RoutingDecision(Enum):
    CACHE_HIT = "cache_hit"
    FAST_PATH = "fast_path"
    FULL_PIPELINE = "full_pipeline"

@dataclass
class RoutingResult:
    decision: RoutingDecision
    query_type: QueryType
    cached_response: Optional[QueryResponse] = None
    reasoning: str = ""

SIMPLE_QUERY_PATTERNS = [
    r"^what is", r"^who is", r"^when did", r"^where is",
    r"^define ", r"^what does", r"^simple question",
    r"^[a-z]+ [a-z]+ [a-z]+[?]$"
]

COMPLEX_QUERY_PATTERNS = [
    r"(compare|analyze|evaluate|assess)",
    r"(prove|disprove|demonstrate)",
    r"(comprehensive|detailed|in-depth)",
    r"(true or false|fact-check|verify)",
    r"(real or fake|legit|scam)",
    r"(conspiracy|misinformation|disinformation)",
    r"(contradiction|inconsisten)",
    r"(bias|propaganda)"
]

TRIGGER_WORDS = ["fake", "false", "misinformation", "disinformation", "scam", "hoax", "conspiracy"]

class QueryClassifier:
    """
    Lightweight regex-based classifier for instant query categorization.
    Phase 5 will supplement this with a Small LLM path.
    """
    def __init__(self):
        self._simple_patterns = [re.compile(p, re.I) for p in SIMPLE_QUERY_PATTERNS]
        self._complex_patterns = [re.compile(p, re.I) for p in COMPLEX_QUERY_PATTERNS]
        self._trigger_set = set(t.lower() for t in TRIGGER_WORDS)

    def classify(self, query: str) -> QueryType:
        query_lower = query.lower().strip()

        # 1. Check for simple patterns (high speed)
        if any(p.match(query_lower) for p in self._simple_patterns):
            if len(query_lower.split()) <= 10 and not any(t in query_lower for t in self._trigger_set):
                return QueryType.SIMPLE

        # 2. Check for complex patterns or trigger words
        if any(p.search(query_lower) for p in self._complex_patterns) or \
           any(t in query_lower for t in self._trigger_set):
            return QueryType.COMPLEX

        # 3. Fallback based on length
        word_count = len(query_lower.split())
        if word_count <= 5:
            return QueryType.SIMPLE
        elif word_count >= 20:
            return QueryType.COMPLEX

        return QueryType.FACTUAL

class QueryRouter:
    """
    Orchestrates query routing: Cache -> Classification -> Path Selection.
    Implements Phase 2: Smart Routing Layer.
    """
    def __init__(self):
        self.classifier = QueryClassifier()
        self._local_cache: TTLCache = TTLCache(maxsize=1000, ttl=300)
        self._metrics: Dict[str, List[float]] = {
            "cache_hit": [], "fast_path": [], "full_pipeline": []
        }

    def _generate_cache_key(self, query: str) -> str:
        normalized = " ".join(query.lower().strip().split())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    async def route(self, query: str) -> RoutingResult:
        start_time = time.time()
        
        # 1. Instant Cache Check (Local -> Redis)
        # This implements 'Cached query -> return instantly'
        cache_key = self._generate_cache_key(query)
        cached = self._local_cache.get(cache_key)
        
        if not cached:
            cached = await redis_cache.get(query)
            if cached:
                self._local_cache[cache_key] = cached

        if cached:
            self._metrics["cache_hit"].append(time.time() - start_time)
            return RoutingResult(
                decision=RoutingDecision.CACHE_HIT,
                query_type=QueryType.FACTUAL,
                cached_response=cached,
                reasoning="Result served from low-latency cache layer."
            )

        # 2. Query Classification
        query_type = self.classifier.classify(query)

        # 3. Decision Logic
        if query_type == QueryType.SIMPLE:
            return RoutingResult(
                decision=RoutingDecision.FAST_PATH,
                query_type=QueryType.SIMPLE,
                reasoning="Simple query detected. Routing to optimized fast-path pipeline."
            )

        return RoutingResult(
            decision=RoutingDecision.FULL_PIPELINE,
            query_type=query_type,
            reasoning=f"Complex {query_type.value} query. Executing full multi-agent verification."
        )

    def log_metric(self, decision: str, latency: float):
        if decision in self._metrics:
            self._metrics[decision].append(latency)

    def get_metrics(self) -> Dict[str, Any]:
        return {
            route: {
                "count": len(lats),
                "avg_ms": round(sum(lats) / len(lats) * 1000, 2) if lats else 0
            }
            for route, lats in self._metrics.items()
        }

router = QueryRouter()

async def route_and_execute(
    query: str,
    fast_pipeline_fn: Callable[[str], Awaitable[QueryResponse]],
    full_pipeline_fn: Callable[[str], Awaitable[QueryResponse]]
) -> tuple[QueryResponse, RoutingResult]:
    """
    Unified entry point for execution based on routing decisions.
    """
    start_time = time.time()
    result = await router.route(query)

    if result.decision == RoutingDecision.CACHE_HIT and result.cached_response:
        return result.cached_response, result

    if result.decision == RoutingDecision.FAST_PATH:
        response = await fast_pipeline_fn(query)
        latency = time.time() - start_time
        router.log_metric("fast_path", latency)
        # Background cache population
        await redis_cache.set(query, response)
        return response, result

    response = await full_pipeline_fn(query)
    latency = time.time() - start_time
    router.log_metric("full_pipeline", latency)
    # Background cache population
    await redis_cache.set(query, response)
    return response, result

