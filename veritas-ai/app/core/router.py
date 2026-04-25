"""Query routing: fast vs deep pipeline selection."""
from enum import Enum


class RouteDecision(str, Enum):
    FAST = "fast"
    DEEP = "deep"


def route(query: str) -> RouteDecision:
    """Route query to fast or deep pipeline based on complexity."""
    words = query.split()
    if len(words) < 10 or len(query) < 50:
        return RouteDecision.FAST
    trigger_words = {"compare", "analyze", "investigate", "explain why", "deep", "misinformation", "fake"}
    if any(w in query.lower() for w in trigger_words):
        return RouteDecision.DEEP
    return RouteDecision.FAST
