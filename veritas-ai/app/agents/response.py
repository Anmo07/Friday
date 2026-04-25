"""Response agent: builds final QueryResponse from agent results."""
import logging
from datetime import datetime, timezone
from typing import List, Dict

logger = logging.getLogger(__name__)


def _build_summary(query: str, retrieval_data: Dict, validation_data: Dict) -> str:
    """Build a human-readable summary from agent outputs."""
    if validation_data.get("summary"):
        return validation_data["summary"]

    assessment = retrieval_data.get("assessment", "")
    status = validation_data.get("status", "uncertain")
    truth_score = validation_data.get("truth_score", 0.5)
    sources = retrieval_data.get("sources", [])

    if assessment and assessment != "Unable to retrieve sources":
        return assessment

    if status == "verified" and truth_score > 0.75:
        return f"The claim appears to be supported by available evidence (truth score: {truth_score:.2f})."
    if status == "likely_false":
        return f"The claim appears to be unsupported or contradicted by available evidence (truth score: {truth_score:.2f})."
    if not sources:
        return "Insufficient verified evidence was collected to confirm the claim."

    return f"Verification completed for '{query}', but the collected evidence was too sparse for a stronger conclusion."


async def response_agent(query: str, results: List[Dict]) -> Dict:
    """
    Build final response from retrieval + validation results.
    Merges agent outputs into a unified QueryResponse dict.
    """
    retrieval_data = results[0] if len(results) > 0 else {}
    validation_data = results[1] if len(results) > 1 else {}

    # Normalize sources from retrieval into schema-compatible dicts
    raw_sources = retrieval_data.get("sources", [])
    if raw_sources and isinstance(raw_sources[0], str):
        sources = [
            {"url": s, "credibility_score": 0.5, "type": "unknown"}
            for s in raw_sources
        ]
    elif raw_sources and isinstance(raw_sources[0], dict):
        sources = raw_sources
    else:
        sources = []

    # Compute evidence coverage for confidence refinement (from old response_builder)
    facts = validation_data.get("facts", [])
    evidence_coverage = min(1.0, ((len(facts) * 0.15) + (len(sources) * 0.2)))
    raw_confidence = validation_data.get("confidence_score", 0.5)
    confidence_score = round((raw_confidence + evidence_coverage) / 2, 3)

    response = {
        "query": query,
        "summary": _build_summary(query, retrieval_data, validation_data),
        "facts": facts,
        "sources": sources,
        "contradictions": validation_data.get("contradictions", []),
        "fake_probability": validation_data.get("fake_probability", 0.0),
        "confidence_score": confidence_score,
        "truth_score": validation_data.get("truth_score", 0.5),
        "status": validation_data.get("status", "uncertain"),
        "explanation": validation_data.get("explanation", {}),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    return response
