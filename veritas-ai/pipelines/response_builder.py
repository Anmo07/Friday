import re
from datetime import datetime
from typing import Iterable, List, Optional
from urllib.parse import urlparse

from core.truth_engine import TruthEngine
from models.schemas import QueryResponse, Source


URL_PATTERN = re.compile(r"https?://[^\s)\]>\"']+")
FAKE_SCORE_PATTERN = re.compile(r"Classified Label:\s*(?P<label>[A-Z_ -]+)\s*\|\s*NLP Confidence:\s*(?P<score>\d+(?:\.\d+)?)")
SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+")
CONTRADICTION_KEYWORDS = ("contradiction", "conflict", "discrep", "inconsisten", "mismatch")
INVALID_SOURCE_MARKERS = ("example.com", "simulated", "failed to scrape", "no configured news providers available")


def _score_source(url: str) -> Optional[Source]:
    domain = urlparse(url).netloc.lower()
    if not domain or any(marker in domain for marker in ("example.com",)):
        return None

    official_tlds = (".gov", ".edu", ".mil", ".int")
    reliable_media = ("reuters.com", "apnews.com", "bbc.com", "npr.org", "bloomberg.com")
    social_media = ("twitter.com", "x.com", "facebook.com", "reddit.com", "tiktok.com", "instagram.com")

    if domain.endswith(official_tlds):
        return Source(url=url, credibility_score=0.95, type="official")
    if any(reliable in domain for reliable in reliable_media):
        return Source(url=url, credibility_score=0.85, type="media")
    if any(social in domain for social in social_media):
        return Source(url=url, credibility_score=0.30, type="social")
    return Source(url=url, credibility_score=0.50, type="media")


def _dedupe(items: Iterable[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for item in items:
        normalized = " ".join(item.split())
        if not normalized or normalized.lower() in seen:
            continue
        seen.add(normalized.lower())
        ordered.append(normalized)
    return ordered


def _extract_facts(report: str) -> List[str]:
    cleaned = report.replace("\n", " ")
    sentences = [
        sentence.strip()
        for sentence in SENTENCE_SPLIT_PATTERN.split(cleaned)
        if sentence.strip()
    ]

    facts = []
    for sentence in sentences:
        lower_sentence = sentence.lower()
        if len(sentence) < 30:
            continue
        if any(marker in lower_sentence for marker in INVALID_SOURCE_MARKERS):
            continue
        if sentence.startswith("Task") or sentence.startswith("Thought:"):
            continue
        facts.append(sentence)

    return _dedupe(facts)[:5]


def _extract_contradictions(report: str) -> List[str]:
    contradictions = []
    for line in report.splitlines():
        normalized = " ".join(line.split())
        if not normalized:
            continue
        lowered = normalized.lower()
        if "no contradiction" in lowered or "no conflict" in lowered or "no inconsisten" in lowered:
            continue
        if any(keyword in lowered for keyword in CONTRADICTION_KEYWORDS):
            contradictions.append(normalized)
    return _dedupe(contradictions)[:5]


def _extract_sources(report: str) -> List[Source]:
    urls = _dedupe(URL_PATTERN.findall(report))
    sources = [_score_source(url) for url in urls]
    return [source for source in sources if source is not None]


def _extract_fake_probability(report: str) -> float:
    for match in FAKE_SCORE_PATTERN.finditer(report):
        label = match.group("label").strip().lower()
        score = float(match.group("score"))
        if "fake" in label or "misleading" in label:
            return max(0.0, min(score, 1.0))
        if "real" in label or "true" in label:
            return max(0.0, min(1.0 - score, 1.0))
    return 0.5


def _build_summary(query: str, facts: List[str], sources: List[Source], report: str) -> str:
    lower_report = report.lower()
    if not sources:
        return "Insufficient verified evidence was collected to confirm the claim."
    if any(marker in lower_report for marker in INVALID_SOURCE_MARKERS):
        return "Evidence collection returned unverified or unavailable upstream data, so the claim remains uncertain."
    if facts:
        return " ".join(facts[:2])[:500]
    return f"Verification completed for '{query}', but the collected evidence was too sparse for a stronger conclusion."


def build_query_response(query: str, report: str) -> QueryResponse:
    sources = _extract_sources(report)
    facts = _extract_facts(report)
    contradictions = _extract_contradictions(report)
    fake_probability = _extract_fake_probability(report)

    truth_engine = TruthEngine()
    truth_result = truth_engine.compute_truth_score(
        {
            "sources": [source.url for source in sources],
            "agreeing_sources": len([source for source in sources if source.credibility_score >= 0.75]),
            "conflicting_sources": len(contradictions),
            "temporal_anomalies": any(token in report.lower() for token in ("breaking", "urgent", "unconfirmed")),
            "rag_hits": report.count("[Distance:"),
            "kg_hits": report.count("]-> ("),
            "fake_probability": fake_probability,
        }
    )

    evidence_coverage = min(1.0, ((len(facts) * 0.15) + (len(sources) * 0.2)))
    confidence_score = round((truth_result["truth_score"] + evidence_coverage) / 2, 3)

    return QueryResponse(
        query=query,
        summary=_build_summary(query, facts, sources, report),
        facts=facts,
        sources=sources,
        contradictions=contradictions,
        fake_probability=round(fake_probability, 3),
        confidence_score=confidence_score,
        truth_score=truth_result["truth_score"],
        status="uncertain",
        timestamp=datetime.utcnow().isoformat() + "Z",
    )
