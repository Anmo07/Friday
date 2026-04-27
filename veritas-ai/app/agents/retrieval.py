"""Retrieval agent: async source fetching and credibility scoring."""
import asyncio
import logging
from typing import Dict, List

from models.ollama_runtime import (
    OllamaModelUnavailableError,
    create_ollama_llm,
    require_model_name,
)

logger = logging.getLogger(__name__)

# Source authority scoring (from old core/truth_engine.py)
DOMAIN_AUTHORITY = {
    ".gov": 1.0,
    ".edu": 0.95,
    "reuters.com": 0.9,
    "apnews.com": 0.9,
    "bbc.com": 0.85,
    "nytimes.com": 0.85,
    "washingtonpost.com": 0.8,
}


def _score_source_authority(url: str) -> float:
    """Score source credibility based on domain."""
    url_lower = url.lower()
    for domain, score in DOMAIN_AUTHORITY.items():
        if domain in url_lower:
            return score
    if any(s in url_lower for s in [".gov", ".edu", ".org"]):
        return 0.8
    if any(
        s in url_lower
        for s in ["twitter.com", "facebook.com", "reddit.com", "tiktok.com"]
    ):
        return 0.3
    return 0.5


async def retrieval_agent(query: str) -> Dict:
    """
    Retrieve and score sources for a query.
    Uses Ollama LLM to identify relevant source types and generate
    credibility assessment. Non-blocking async execution.
    """
    try:
        from app.core.config import settings

        model_name = require_model_name(
            [settings.FAST_MODEL, settings.MODEL_NAME, settings.ROUTER_MODEL],
            base_url=settings.OLLAMA_BASE_URL,
        )
        llm = create_ollama_llm(
            base_url=settings.OLLAMA_BASE_URL,
            model=model_name,
            temperature=0.0,
        )

        prompt = f"""Analyze this claim and provide a brief factual assessment.
Claim: {query}

Respond in this exact format:
ASSESSMENT: [one sentence assessment]
SOURCES_NEEDED: [comma-separated list of source types needed to verify]
INITIAL_CREDIBILITY: [float 0.0-1.0 based on how verifiable this claim is]"""

        # Run LLM in thread pool (Ollama client is sync)
        result = await asyncio.to_thread(llm.invoke, prompt)

        # Parse LLM response
        lines = result.strip().split("\n")
        assessment = ""
        sources_needed: List[str] = []
        credibility = 0.5

        for line in lines:
            if line.startswith("ASSESSMENT:"):
                assessment = line.split(":", 1)[1].strip()
            elif line.startswith("SOURCES_NEEDED:"):
                sources_needed = [s.strip() for s in line.split(":", 1)[1].split(",")]
            elif line.startswith("INITIAL_CREDIBILITY:"):
                try:
                    credibility = float(line.split(":", 1)[1].strip())
                    credibility = max(0.0, min(1.0, credibility))
                except ValueError:
                    credibility = 0.5

        return {
            "query": query,
            "assessment": assessment,
            "sources_needed": sources_needed,
            "source_credibility": credibility,
            "sources": [],  # Actual URLs would come from web scraping in production
            "authority_score": credibility,
            "retrieval_complete": True,
        }
    except OllamaModelUnavailableError as e:
        logger.info(f"Retrieval agent using fallback: {e}")
        return {
            "query": query,
            "assessment": "No local Ollama model is installed, so I used the lightweight fallback.",
            "sources_needed": [],
            "source_credibility": 0.5,
            "sources": [],
            "authority_score": 0.5,
            "retrieval_complete": False,
        }
    except Exception as e:
        logger.warning(f"Retrieval agent failed, using fallback: {e}")
        return {
            "query": query,
            "assessment": "Unable to retrieve sources",
            "sources_needed": [],
            "source_credibility": 0.5,
            "sources": [],
            "authority_score": 0.5,
            "retrieval_complete": False,
        }
