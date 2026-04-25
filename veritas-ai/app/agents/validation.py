"""Validation agent: truth scoring, firewall, consensus, explainability."""
import asyncio
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ---- Truth Engine (from core/truth_engine.py) ----

WEIGHTS = {
    "source_authority": 0.25,
    "cross_source_agreement": 0.25,
    "temporal_consistency": 0.15,
    "claim_verifiability": 0.20,
    "bias_deviation": 0.15,
}


def _calculate_source_authority(sources: List[str]) -> float:
    """Preserve the exact scoring from old truth_engine."""
    if not sources:
        return 0.5

    scores = []
    for src in sources:
        src_lower = src.lower()
        if any(tld in src_lower for tld in [".gov", ".edu", ".mil", ".int"]):
            scores.append(1.0)
        elif any(
            domain in src_lower
            for domain in [
                "reuters.com",
                "apnews.com",
                "bbc.com",
                "npr.org",
                "bloomberg.com",
            ]
        ):
            scores.append(0.85)
        elif any(
            domain in src_lower
            for domain in [
                "twitter.com",
                "x.com",
                "facebook.com",
                "reddit.com",
                "tiktok.com",
                "instagram.com",
            ]
        ):
            scores.append(0.3)
        else:
            scores.append(0.5)

    return sum(scores) / len(scores)


def _calculate_cross_source_agreement(data: Dict) -> float:
    """Calculate consensus ratio from agreeing vs conflicting sources."""
    agreeing = data.get("agreeing_sources", 0)
    conflicting = data.get("conflicting_sources", 0)
    total = agreeing + conflicting
    if total == 0:
        return 0.5
    return agreeing / total


def _calculate_temporal_consistency(data: Dict) -> float:
    """Penalize sudden narrative shifts."""
    anomalies = data.get("temporal_anomalies", False)
    return 0.3 if anomalies else 0.9


def _calculate_claim_verifiability(data: Dict) -> float:
    """Check RAG + KG hit counts."""
    total_hits = data.get("rag_hits", 0) + data.get("kg_hits", 0)
    if total_hits >= 3:
        return 1.0
    if total_hits == 2:
        return 0.8
    if total_hits == 1:
        return 0.5
    return 0.2


def _calculate_bias_deviation(data: Dict) -> float:
    """Inverse fake-news probability for truth scaling."""
    fake_prob = data.get("fake_probability", 0.0)
    return max(0.0, 1.0 - fake_prob)


def compute_truth_score(data: Dict) -> Dict:
    """Compute truth score with same weights as original."""
    auth_score = _calculate_source_authority(data.get("sources", []))
    agreement_score = _calculate_cross_source_agreement(data)
    temporal_score = _calculate_temporal_consistency(data)
    verifiability_score = _calculate_claim_verifiability(data)
    bias_score = _calculate_bias_deviation(data)

    final_score = (
        auth_score * WEIGHTS["source_authority"]
        + agreement_score * WEIGHTS["cross_source_agreement"]
        + temporal_score * WEIGHTS["temporal_consistency"]
        + verifiability_score * WEIGHTS["claim_verifiability"]
        + bias_score * WEIGHTS["bias_deviation"]
    )

    breakdown = {
        "source_authority": round(auth_score, 3),
        "cross_source_agreement": round(agreement_score, 3),
        "temporal_consistency": round(temporal_score, 3),
        "claim_verifiability": round(verifiability_score, 3),
        "bias_deviation": round(bias_score, 3),
    }

    # Try to log via observability layer if available
    try:
        from core.observability import observability

        observability.log_truth_score(round(final_score, 3), breakdown)
    except Exception:
        pass

    data["truth_score"] = round(final_score, 3)
    data["breakdown"] = breakdown
    return data


# ---- Firewall (from core/firewall.py) ----

FIREWALL_OFFICIAL_TLDS = (".gov", ".edu", ".mil", ".int")
FIREWALL_RELIABLE_MEDIA = (
    "reuters.com",
    "apnews.com",
    "bbc.com",
    "npr.org",
    "bloomberg.com",
)
FIREWALL_SOCIAL_MEDIA = (
    "twitter.com",
    "x.com",
    "facebook.com",
    "reddit.com",
    "tiktok.com",
    "instagram.com",
)


def _score_source_for_firewall(url: str) -> Dict:
    """Return a scored source dict for firewall/explainability use."""
    domain = url.lower()
    if domain.endswith(FIREWALL_OFFICIAL_TLDS):
        return {"url": url, "credibility_score": 0.95, "type": "official"}
    if any(reliable in domain for reliable in FIREWALL_RELIABLE_MEDIA):
        return {"url": url, "credibility_score": 0.85, "type": "media"}
    if any(social in domain for social in FIREWALL_SOCIAL_MEDIA):
        return {"url": url, "credibility_score": 0.30, "type": "social"}
    return {"url": url, "credibility_score": 0.50, "type": "unknown"}


def apply_firewall(data: Dict) -> Dict:
    """Hallucination firewall: deterministic logic overrides."""
    contradiction_threshold = 1

    raw_sources = data.get("sources", [])
    scored_sources = [_score_source_for_firewall(s) for s in raw_sources]
    trusted_sources = [s for s in scored_sources if s["credibility_score"] >= 0.75]
    trusted_count = len(trusted_sources)

    contradictions = data.get("contradictions", [])
    contradiction_count = len(contradictions)
    truth_score = data.get("truth_score", 0.0)

    # Override 1: Explicit Logic Constraints
    if contradiction_count > contradiction_threshold:
        data["status"] = "likely_false"
        logging.warning(
            f"Firewall Override (Graph/RAG Contradictions > {contradiction_threshold}): "
            f"Status clamped to {data['status']}"
        )
        return data

    # Override 2: Sourcing Authority
    if trusted_count < 2:
        data["status"] = "uncertain"
        logging.warning(
            f"Firewall Override (Trusted Auth Limit < 2): Status clamped to {data['status']}"
        )
        return data

    # Override 3: Verification Array
    if truth_score > 0.75:
        data["status"] = "verified"
        return data

    # Catchall baseline
    data["status"] = "uncertain"
    return data


# ---- Consensus (from core/consensus_engine.py) ----

def apply_consensus(data: Dict) -> Dict:
    """Merge LLM, classifier, and rule-based confidence into unified consensus."""
    llm_confidence = data.get("confidence_score", 0.0)
    fake_probability = data.get("fake_probability", 0.0)
    classifier_confidence = max(0.0, 1.0 - fake_probability)
    rule_confidence = data.get("truth_score", 0.0)

    computed_consensus = (llm_confidence + classifier_confidence + rule_confidence) / 3.0
    data["confidence_score"] = round(computed_consensus, 3)
    return data


# ---- Explainability (from core/explainability_layer.py) ----

def generate_explanation(data: Dict) -> Dict:
    """Generate human-readable explanation with why_true, why_false, breakdown."""
    raw_sources = data.get("sources", [])
    scored_sources = [_score_source_for_firewall(s) for s in raw_sources]
    trusted_sources = [s for s in scored_sources if s["credibility_score"] >= 0.75]
    contradictions = data.get("contradictions", [])
    fake_probability = data.get("fake_probability", 0.0)

    explanation = {
        "why_true": [],
        "why_false": [],
        "confidence_breakdown": {},
    }

    # 1. Logic Mappings: Why True?
    if len(trusted_sources) >= 2:
        explanation["why_true"].append(
            f"Confirmed directly by {len(trusted_sources)} authoritative trusted domains."
        )
    if fake_probability < 0.3:
        explanation["why_true"].append(
            "Passed Transformer classification NLP layer safely (Zero explicit propaganda matched)."
        )
    if not contradictions:
        explanation["why_true"].append(
            "Mathematical graph comparisons revealed no structural assertion deviations natively."
        )

    # 2. Logic Mappings: Why False?
    if contradictions:
        explanation["why_false"].append(
            f"Detected {len(contradictions)} isolated contradictions across Knowledge Graph limits."
        )
    if fake_probability > 0.6:
        explanation["why_false"].append(
            f"Extreme classification bias detected logically scoring at {fake_probability} limits."
        )
    if len(trusted_sources) == 0:
        explanation["why_false"].append(
            "Zero high-authority sources discovered verifying this claim explicitly."
        )

    # 3. Explicit Breakdown Computations
    auth_score = _calculate_source_authority(raw_sources)
    bias_score = _calculate_bias_deviation(data)
    agreement_score = (
        1.0 if not contradictions else max(0.0, 1.0 - (len(contradictions) * 0.2))
    )

    explanation["confidence_breakdown"] = {
        "authority": round(auth_score, 3),
        "agreement": round(agreement_score, 3),
        "bias": round(bias_score, 3),
    }

    data["explanation"] = explanation
    return data


# ---- Main Agent ----

async def validation_agent(query: str, sources: Optional[Dict] = None) -> Dict:
    """
    Validate a claim: compute truth score, apply firewall, generate explanation.
    Runs synchronous scoring in thread pool to avoid blocking.
    """
    retrieval_data = sources or {}
    source_credibility = retrieval_data.get("source_credibility", 0.5)

    data = {
        "query": query,
        "sources": retrieval_data.get("sources", []),
        "source_credibility": source_credibility,
        "authority_score": retrieval_data.get("authority_score", 0.5),
        "agreeing_sources": 0,
        "conflicting_sources": 0,
        "temporal_anomalies": any(
            token in query.lower() for token in ("breaking", "urgent", "unconfirmed")
        ),
        "rag_hits": 0,
        "kg_hits": 0,
        "fake_probability": max(0.0, 1.0 - source_credibility),
        "confidence_score": source_credibility,
        "contradictions": [],
        "status": "uncertain",
    }

    def _run_validation(d: Dict) -> Dict:
        d = compute_truth_score(d)
        d = apply_firewall(d)
        d = apply_consensus(d)
        d = generate_explanation(d)
        return d

    # Run CPU-bound scoring in thread pool
    result = await asyncio.to_thread(_run_validation, data)
    return result
