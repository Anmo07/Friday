import logging
from typing import Dict

logger = logging.getLogger(__name__)
EMOTION_KEYWORDS: Dict[str, list] = {
    "urgent": [
        "breaking",
        "urgent",
        "emergency",
        "alert",
        "critical",
        "warning",
        "danger",
    ],
    "concerned": [
        "worried",
        "concerned",
        "suspicious",
        "doubt",
        "question",
        "uncertain",
        "fake",
        "false",
        "misinformation",
    ],
    "positive": [
        "great",
        "good",
        "excellent",
        "verified",
        "confirmed",
        "true",
        "accurate",
        "reliable",
    ],
    "negative": [
        "bad",
        "wrong",
        "incorrect",
        "misleading",
        "propaganda",
        "hoax",
        "debunked",
        "lie",
    ],
    "neutral": [],
}
EMOTION_VOICE_MAP = {
    "urgent": {"rate": "+15%", "pitch": "+5Hz"},
    "concerned": {"rate": "+0%", "pitch": "-2Hz"},
    "positive": {"rate": "+0%", "pitch": "+2Hz"},
    "negative": {"rate": "-5%", "pitch": "-3Hz"},
    "neutral": {"rate": "+0%", "pitch": "+0Hz"},
}


def detect_emotion(text: str) -> str:
    if not text:
        return "neutral"
    text_lower = text.lower()
    scores = {}
    for emotion, keywords in EMOTION_KEYWORDS.items():
        if emotion == "neutral":
            continue
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[emotion] = score
    if not scores:
        return "neutral"
    return max(scores, key=scores.get)


def get_voice_adjustment(emotion: str) -> Dict[str, str]:
    return EMOTION_VOICE_MAP.get(emotion, EMOTION_VOICE_MAP["neutral"])
