import hashlib
import re
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Callable, Awaitable

from cachetools import TTLCache

from config.settings import settings
from models.schemas import QueryResponse


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
    r"^what is",
    r"^who is",
    r"^when did",
    r"^where is",
    r"^define ",
    r"^what does",
    r"^simple question",
    r"^[a-z]+ [a-z]+ [a-z]+[?]$",
]

COMPLEX_QUERY_PATTERNS = [
    r"(compare|analyze|evaluate|assess)",
    r"(prove|disprove|demonstrate)",
    r"(comprehensive|detailed|in-depth)",
    r"(true or false|fact-check|verify)",
    r"(real or fake|legit|scam)",
    r"(conspiracy|misinformation|disinformation)",
    r"(contradiction|inconsisten)",
    r"(bias|propaganda)",
]

TRIGGER_WORDS = [
    "fake",
    "false",
    "misinformation",
    "disinformation",
    "scam",
    "hoax",
    "conspiracy",
]


class QueryClassifier:
    def __init__(self):
        self._simple_patterns = [re.compile(p, re.I) for p in SIMPLE_QUERY_PATTERNS]
        self._complex_patterns = [re.compile(p, re.I) for p in COMPLEX_QUERY_PATTERNS]
        self._trigger_set = set(t.lower() for t in TRIGGER_WORDS)

    def classify(self, query: str) -> QueryType:
        query_lower = query.lower().strip()

        if any(p.match(query_lower) for p in self._simple_patterns):
            word_count = len(query_lower.split())
            if word_count <= 8 and not any(t in query_lower for t in self._trigger_set):
                return QueryType.SIMPLE

        if any(p.search(query_lower) for p in self._complex_patterns):
            return QueryType.COMPLEX

        if any(t in query_lower for t in self._trigger_set):
            return QueryType.COMPLEX

        word_count = len(query_lower.split())
        if word_count <= 5:
            return QueryType.SIMPLE
        elif word_count >= 15:
            return QueryType.COMPLEX

        return QueryType.FACTUAL


class QueryRouter:
    def __init__(self):
        self.classifier = QueryClassifier()
        self._response_cache: TTLCache = TTLCache(
            maxsize=settings.CACHE_MAX_ENTRIES,
            ttl=settings.CACHE_TTL_SECONDS,
        )
        self._metrics: Dict[str, List[float]] = {
            "cache_hit": [],
            "fast_path": [],
            "full_pipeline": [],
        }

    def _normalize_query(self, query: str) -> str:
        return " ".join(query.lower().strip().split())

    def _generate_cache_key(self, query: str) -> str:
        normalized = self._normalize_query(query)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def check_cache(self, query: str) -> Optional[QueryResponse]:
        cache_key = self._generate_cache_key(query)
        cached = self._response_cache.get(cache_key)
        if cached is not None:
            start_time = getattr(self, "_last_request_time", time.time())
            latency = time.time() - start_time
            self._metrics["cache_hit"].append(latency)
        return cached

    def cache_response(self, query: str, response: QueryResponse) -> None:
        cache_key = self._generate_cache_key(query)
        self._response_cache[cache_key] = response

    def route(self, query: str) -> RoutingResult:
        self._last_request_time = time.time()

        cached = self.check_cache(query)
        if cached is not None:
            return RoutingResult(
                decision=RoutingDecision.CACHE_HIT,
                query_type=QueryType.FACTUAL,
                cached_response=cached,
                reasoning="Exact query match found in cache",
            )

        query_type = self.classifier.classify(query)

        if query_type == QueryType.SIMPLE:
            return RoutingResult(
                decision=RoutingDecision.FAST_PATH,
                query_type=QueryType.SIMPLE,
                reasoning="Simple query detected - using fast path",
            )

        return RoutingResult(
            decision=RoutingDecision.FULL_PIPELINE,
            query_type=query_type,
            reasoning=f"{query_type.value} query - running full verification pipeline",
        )

    def get_metrics(self) -> Dict[str, Dict[str, float]]:
        result = {}
        for route, latencies in self._metrics.items():
            if latencies:
                result[route] = {
                    "count": len(latencies),
                    "avg_latency_ms": sum(latencies) / len(latencies) * 1000,
                    "min_latency_ms": min(latencies) * 1000,
                    "max_latency_ms": max(latencies) * 1000,
                }
        return result


router = QueryRouter()


async def route_and_execute(
    query: str,
    fast_pipeline_fn: Callable[[str], Awaitable[QueryResponse]],
    full_pipeline_fn: Callable[[str], Awaitable[QueryResponse]],
) -> tuple[QueryResponse, RoutingResult]:
    result = router.route(query)

    if result.decision == RoutingDecision.CACHE_HIT and result.cached_response:
        return result.cached_response, result

    if result.decision == RoutingDecision.FAST_PATH:
        response = await fast_pipeline_fn(query)
        router.cache_response(query, response)
        return response, result

    response = await full_pipeline_fn(query)
    router.cache_response(query, response)
    return response, result
