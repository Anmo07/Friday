"""Assistant orchestration: personality, intent routing, task-first execution."""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Awaitable, Callable, Literal
from urllib.parse import quote_plus, urlparse

from app.pipeline.deep_pipeline import deep_pipeline
from app.pipeline.fast_pipeline import fast_pipeline
from core.personality import friday_personality
from system.control_engine import control_engine

logger = logging.getLogger(__name__)


AssistantMode = Literal["assistant", "verification"]
IntentKind = Literal["control", "news", "verification", "chat", "interrupt"]
ProgressCallback = Callable[[str, str], Awaitable[None]]


CONTROL_PREFIXES = (
    "open ",
    "launch ",
    "start ",
    "close ",
    "quit ",
    "stop ",
    "run ",
    "execute ",
    "terminal ",
    "search file ",
    "find file ",
    "open browser ",
    "browse ",
    "search web for ",
    "google ",
    "shutdown",
)

NEWS_TERMS = (
    "latest news",
    "news about",
    "headlines",
    "breaking news",
    "latest on",
)

FILTER_TERMS = (
    "reliable sources only",
    "filter sources",
    "remove unreliable",
)

VERIFICATION_TERMS = (
    "verify",
    "verification",
    "fact check",
    "fact-check",
    "true or false",
    "is this true",
    "debunk",
    "investigate",
    "deep dive",
    "explain why",
    "compare",
    "analyze",
)


@dataclass(frozen=True)
class AssistantIntent:
    raw_query: str
    normalized_query: str
    mode: AssistantMode
    kind: IntentKind
    deep: bool
    opening_line: str


def _score_source(url: str) -> float:
    lowered = url.lower()
    if any(domain in lowered for domain in ("reuters.com", "apnews.com", "bbc.com", "npr.org", "gov")):
        return 0.9
    if any(domain in lowered for domain in ("nytimes.com", "washingtonpost.com", "theguardian.com")):
        return 0.8
    return 0.65


def _source_type(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host.endswith((".gov", ".edu", ".mil")):
        return "official"
    if any(domain in host for domain in ("reuters.com", "apnews.com", "bbc.com", "npr.org", "cnn.com")):
        return "media"
    if any(domain in host for domain in ("reddit.com", "x.com", "twitter.com", "facebook.com")):
        return "social"
    return "unknown"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_assistant_response(
    query: str,
    summary: str,
    *,
    mode: AssistantMode,
    intent: IntentKind,
    facts: list[str] | None = None,
    sources: list[dict] | None = None,
    status: Literal["verified", "likely_false", "uncertain"] = "verified",
    confidence: float = 0.92,
    truth_score: float = 0.92,
    explanation: dict | None = None,
    **extras,
) -> dict:
    return {
        "query": query,
        "summary": friday_personality.polish_response(summary, mode=mode),
        "facts": facts or [],
        "sources": sources or [],
        "contradictions": [],
        "fake_probability": round(max(0.0, 1.0 - truth_score), 3),
        "confidence_score": round(confidence, 3),
        "truth_score": round(truth_score, 3),
        "status": status,
        "explanation": explanation,
        "timestamp": _now_iso(),
        "assistant_mode": mode,
        "intent": intent,
        **extras,
    }


class AssistantOrchestrator:
    """Classify requests and execute the fastest useful path."""

    def classify(self, query: str, *, deep_requested: bool = False) -> AssistantIntent:
        normalized = " ".join(query.strip().split())
        lowered = normalized.lower()

        if friday_personality.detect_interruption(lowered):
            return AssistantIntent(
                raw_query=query,
                normalized_query=normalized,
                mode="assistant",
                kind="interrupt",
                deep=False,
                opening_line=friday_personality.stopping_response(),
            )

        if lowered.startswith("open source "):
            return AssistantIntent(
                raw_query=query,
                normalized_query=normalized,
                mode="verification",
                kind="chat",
                deep=False,
                opening_line=friday_personality.acknowledgement("chat"),
            )

        if lowered.startswith(CONTROL_PREFIXES):
            return AssistantIntent(
                raw_query=query,
                normalized_query=normalized,
                mode="assistant",
                kind="control",
                deep=False,
                opening_line=friday_personality.acknowledgement("control"),
            )

        if any(term in lowered for term in NEWS_TERMS) or any(term in lowered for term in ("show", "analyze deeply", "compare", "focus on reliable")):
            return AssistantIntent(
                raw_query=query,
                normalized_query=normalized,
                mode="verification",
                kind="news",
                deep=True,
                opening_line=friday_personality.acknowledgement("news"),
            )

        wants_verification = deep_requested or any(term in lowered for term in VERIFICATION_TERMS)
        long_query = len(lowered.split()) >= 12
        if wants_verification or long_query:
            return AssistantIntent(
                raw_query=query,
                normalized_query=normalized,
                mode="verification",
                kind="verification",
                deep=True,
                opening_line=friday_personality.acknowledgement("verification"),
            )

        return AssistantIntent(
            raw_query=query,
            normalized_query=normalized,
            mode="assistant",
            kind="chat",
            deep=False,
            opening_line=friday_personality.acknowledgement("chat"),
        )

    async def execute(
        self,
        query: str,
        *,
        deep_requested: bool = False,
        progress_callback: ProgressCallback | None = None,
    ) -> dict:
        intent = self.classify(query, deep_requested=deep_requested)

        if intent.kind == "interrupt":
            return _build_assistant_response(
                intent.normalized_query,
                friday_personality.stopping_response(),
                mode="assistant",
                intent="interrupt",
                confidence=1.0,
                truth_score=1.0,
                status="verified",
                interrupted=True,
            )

        if intent.kind == "control":
            if progress_callback:
                await progress_callback("action", "Running that on your system...")
            result = await control_engine.execute(intent.normalized_query)
            details = result.details.copy()
            facts = []
            if details.get("output"):
                facts.append(details["output"])
            if details.get("matches"):
                facts.extend(details["matches"][:5])
            explanation = {"control": details} if details else None
            status = "verified" if result.success else "uncertain"
            confidence = 0.98 if result.success else 0.45
            truth_score = 1.0 if result.success else 0.4
            return _build_assistant_response(
                intent.normalized_query,
                result.summary,
                mode=intent.mode,
                intent=intent.kind,
                facts=facts,
                status=status,
                confidence=confidence,
                truth_score=truth_score,
                explanation=explanation,
                action=result.action,
                requires_confirmation=result.requires_confirmation,
                executed=result.success,
            )

        if intent.kind == "news" and not intent.deep:
            if progress_callback:
                await progress_callback("news_fetch", "Pulling the latest coverage...")
            return await self._fetch_news_brief(intent.normalized_query)

        if progress_callback:
            await progress_callback(
                "verification" if intent.mode == "verification" else "processing",
                "Working on it...",
            )

        response = (
            await deep_pipeline(intent.normalized_query, progress_callback=progress_callback)
            if intent.deep
            else await fast_pipeline(intent.normalized_query, progress_callback=progress_callback)
        )
        response["summary"] = friday_personality.polish_response(
            response.get("summary", ""),
            mode=intent.mode,
        )
        response["assistant_mode"] = intent.mode
        response["intent"] = intent.kind
        response["timestamp"] = response.get("timestamp") or _now_iso()
        return response

    async def _fetch_news_brief(self, query: str) -> dict:
        search_terms = self._extract_news_topic(query)
        articles = await asyncio.to_thread(self._read_google_news_feed, search_terms)

        if not articles:
            return _build_assistant_response(
                query,
                f"I couldn’t pull fresh coverage on {search_terms} just yet.",
                mode="assistant",
                intent="news",
                status="uncertain",
                confidence=0.35,
                truth_score=0.35,
            )

        sources = [
            {
                "url": article["url"],
                "credibility_score": _score_source(article["url"]),
                "type": _source_type(article["url"]),
            }
            for article in articles
            if article.get("url")
        ]
        facts = [article["title"] for article in articles if article.get("title")]
        summary = friday_personality.build_news_summary(search_terms, facts)
        explanation = {"coverage": articles}
        return _build_assistant_response(
            query,
            summary,
            mode="assistant",
            intent="news",
            facts=facts[:5],
            sources=sources[:5],
            status="verified",
            confidence=0.88,
            truth_score=0.86,
            explanation=explanation,
            topic=search_terms,
        )

    def _extract_news_topic(self, query: str) -> str:
        lowered = query.lower()
        topic = lowered
        replacements = (
            "search latest news about ",
            "latest news about ",
            "latest news on ",
            "latest on ",
            "news about ",
            "headlines about ",
            "breaking news on ",
        )
        for prefix in replacements:
            if lowered.startswith(prefix):
                topic = query[len(prefix):]
                break
        return topic.strip(" ?") or query

    def _read_google_news_feed(self, topic: str) -> list[dict]:
        try:
            import feedparser
        except ImportError:
            logger.warning("feedparser unavailable for news fetch")
            return []

        rss_url = (
            "https://news.google.com/rss/search"
            f"?q={quote_plus(topic)}&hl=en-US&gl=US&ceid=US:en"
        )
        feed = feedparser.parse(rss_url)
        items: list[dict] = []
        for entry in feed.entries[:5]:
            title = re.sub(r"\s*-\s*[^-]+$", "", entry.get("title", "")).strip()
            items.append(
                {
                    "title": title or entry.get("title", ""),
                    "url": entry.get("link", ""),
                    "published": entry.get("published", ""),
                    "source": entry.get("source", {}).get("title", ""),
                }
            )
        return items


assistant_orchestrator = AssistantOrchestrator()
