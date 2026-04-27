"""
Adaptive Depth Router — Phases 1-2

Routes queries to one of three depth levels:
  LEVEL 1 (Fast):     retrieval + response           (~1s)
  LEVEL 2 (Enhanced): retrieval + validation + response  (~2-3s)
  LEVEL 3 (Deep):     full multi-agent suite              (~5-10s)

Decision is instant (regex-based) — zero LLM overhead.
"""

import re
import logging
from enum import IntEnum
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


class DepthLevel(IntEnum):
    FAST = 1
    ENHANCED = 2
    DEEP = 3


@dataclass
class DepthDecision:
    level: DepthLevel
    reasoning: str
    max_agents: int
    max_sources: int
    max_llm_calls: int


# ---------------------------------------------------------------------------
# Pattern banks
# ---------------------------------------------------------------------------

DEEP_TRIGGERS = re.compile(
    r"(analyze\s+deeply|in-depth|compare\s+\w+|news\s+breakdown|"
    r"full\s+analysis|deep\s+dive|show\s+all\s+perspectives|"
    r"multiple\s+viewpoints|investigate|comprehensive|"
    r"prove|disprove|conspiracy|propaganda|bias\s+analysis|"
    r"contradiction|misinformation|disinformation)",
    re.IGNORECASE,
)

ENHANCED_TRIGGERS = re.compile(
    r"(verify|fact[\s-]?check|is\s+(?:it|this|that)\s+true|"
    r"reliable|credible|legit|accurate|real\s+or\s+fake|"
    r"true\s+or\s+false|confirm|debunk|scam|hoax|"
    r"fake\s+news|validate|evidence)",
    re.IGNORECASE,
)

SIMPLE_PATTERNS = re.compile(
    r"^(what\s+is|who\s+is|when\s+did|where\s+is|define\s+|"
    r"how\s+old|tell\s+me\s+about|what\s+does)\b",
    re.IGNORECASE,
)

# Voice command patterns that map to UI actions
VOICE_COMMANDS = {
    re.compile(r"show\s+more\s+sources", re.I): "expand_sources",
    re.compile(r"focus\s+on\s+reliable", re.I): "filter_reliable",
    re.compile(r"expand\s+this\s+result", re.I): "expand_frame",
    re.compile(r"switch\s+to\s+deep", re.I): "force_deep",
    re.compile(r"show\s+contradictions", re.I): "show_contradictions",
}


def classify_depth(query: str, force_deep: bool = False) -> DepthDecision:
    """
    Classify query into a depth level. Zero LLM cost.

    Priority: force_deep > DEEP patterns > ENHANCED patterns > SIMPLE patterns > word-count fallback
    """
    normalized = " ".join(query.strip().split())

    if force_deep:
        return DepthDecision(
            level=DepthLevel.DEEP,
            reasoning="User explicitly requested deep analysis.",
            max_agents=5,
            max_sources=5,
            max_llm_calls=2,
        )

    if DEEP_TRIGGERS.search(normalized):
        return DepthDecision(
            level=DepthLevel.DEEP,
            reasoning="Query contains deep-analysis trigger words.",
            max_agents=5,
            max_sources=5,
            max_llm_calls=2,
        )

    if ENHANCED_TRIGGERS.search(normalized):
        return DepthDecision(
            level=DepthLevel.ENHANCED,
            reasoning="Query requires verification/validation.",
            max_agents=3,
            max_sources=4,
            max_llm_calls=2,
        )

    if SIMPLE_PATTERNS.match(normalized):
        word_count = len(normalized.split())
        if word_count <= 10:
            return DepthDecision(
                level=DepthLevel.FAST,
                reasoning="Simple factual query detected.",
                max_agents=2,
                max_sources=3,
                max_llm_calls=1,
            )

    # Fallback: word count heuristic
    word_count = len(normalized.split())
    if word_count <= 8:
        return DepthDecision(
            level=DepthLevel.FAST,
            reasoning="Short query — fast path.",
            max_agents=2,
            max_sources=3,
            max_llm_calls=1,
        )
    elif word_count >= 20:
        return DepthDecision(
            level=DepthLevel.DEEP,
            reasoning="Long, complex query detected.",
            max_agents=5,
            max_sources=5,
            max_llm_calls=2,
        )

    return DepthDecision(
        level=DepthLevel.ENHANCED,
        reasoning="Moderate query complexity.",
        max_agents=3,
        max_sources=4,
        max_llm_calls=2,
    )


def detect_voice_command(query: str) -> Optional[str]:
    """Check if query is a voice command rather than a search query."""
    normalized = " ".join(query.strip().split()).lower()
    for pattern, action in VOICE_COMMANDS.items():
        if pattern.search(normalized):
            return action
    return None
