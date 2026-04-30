from __future__ import annotations
import logging
import socket
from typing import Any
import requests
from app.core.config import settings

logger = logging.getLogger(__name__)


def is_online(host: str = "1.1.1.1", port: int = 53, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def should_enrich(query: str) -> bool:
    lowered = query.lower()
    triggers = (
        "latest",
        "current",
        "today",
        "price",
        "news",
        "who is",
        "what is",
        "when",
        "where",
    )
    return any(token in lowered for token in triggers)


def fetch_web_context(query: str) -> list[dict[str, Any]]:
    if not settings.WEB_ENRICHMENT_ENABLED:
        return []
    if not is_online():
        return []
    timeout = settings.WEB_ENRICHMENT_TIMEOUT_SECONDS
    results: list[dict[str, Any]] = []
    try:
        response = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": 1, "no_redirect": 1},
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        logger.debug("Web enrichment lookup failed: %s", exc)
        return []
    abstract = payload.get("AbstractText", "").strip()
    abstract_url = payload.get("AbstractURL", "").strip()
    if abstract:
        results.append(
            {
                "title": payload.get("Heading") or query,
                "snippet": abstract,
                "url": abstract_url or "https://duckduckgo.com/",
                "source": "duckduckgo",
            }
        )
    related = payload.get("RelatedTopics", [])
    for topic in related:
        if len(results) >= settings.WEB_ENRICHMENT_MAX_RESULTS:
            break
        if isinstance(topic, dict) and topic.get("Text"):
            results.append(
                {
                    "title": topic.get("Text", "").split(" - ", 1)[0],
                    "snippet": topic.get("Text", ""),
                    "url": topic.get("FirstURL", "https://duckduckgo.com/"),
                    "source": "duckduckgo",
                }
            )
    return results[: settings.WEB_ENRICHMENT_MAX_RESULTS]
