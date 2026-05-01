from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Dict, Any, Optional
import re

INTERRUPTION_PHRASES = (
    "stop",
    "wait",
    "cancel",
    "hold on",
)
FILLER_PHRASES = (
    "I think",
    "It seems",
    "It appears",
    "Actually",
    "Well",
    "So",
)

# Emotional intelligence enhancements
EMOTION_KEYWORDS = {
    "frustrated": ["frustrated", "annoyed", "angry", "upset", "irritated"],
    "confused": ["confused", "don't understand", "unclear", "lost", "puzzled"],
    "excited": ["excited", "happy", "great", "awesome", "fantastic", "wonderful"],
    "sad": ["sad", "unhappy", "depressed", "down", "miserable"],
    "grateful": ["thank", "thanks", "grateful", "appreciate"],
    "urgent": ["urgent", "asap", "quickly", "hurry", "emergency", "important"]
}


@dataclass(frozen=True)
class FridayGreeting:
    period: str
    message: str


class FridayPersonality:
    TRAITS = {
        "casual": True,
        "intelligent": True,
        "light_humor": True,
        "calls_user_boss": True,
        "short_responses": True,
        "task_first": True,
    }
    ASSISTANT_PROMPT = (
        "You are FRIDAY, a voice-first AI assistant. "
        "You speak like a smart adult with light wit. "
        "Keep responses short, natural, and useful. "
        "Address the user as Boss. "
        "Default to action first, analysis second."
    )
    VERIFICATION_PROMPT = (
        "You are FRIDAY in verification mode. "
        "Be concise, grounded, and direct. "
        "Address the user as Boss. "
        "Explain uncertainty plainly without sounding robotic."
    )

    @staticmethod
    def startup_greeting(now: datetime | None = None) -> FridayGreeting:
        current = now or datetime.now()
        hour = current.hour
        if 5 <= hour < 12:
            return FridayGreeting(
                period="morning",
                message="Good morning, Boss. Ready to get things done?",
            )
        if hour >= 17:
            return FridayGreeting(
                period="evening",
                message="Good evening, Boss. What are we working on today?",
            )
        return FridayGreeting(period="neutral", message="Hello Boss.")

    @staticmethod
    def get_system_prompt(mode: str = "assistant", context: str = "normal") -> str:
        base_prompt = (
            FridayPersonality.VERIFICATION_PROMPT
            if mode == "verification"
            else FridayPersonality.ASSISTANT_PROMPT
        )
        if context == "urgent":
            return (
                base_prompt
                + " Prioritize the next useful step and keep it under two sentences."
            )
        if context == "interruption":
            return base_prompt + " Stop immediately and acknowledge the interruption."
        return base_prompt

    @staticmethod
    def detect_interruption(text: str | None) -> bool:
        if not text:
            return False
        normalized = " ".join(text.lower().strip().split())
        return normalized in INTERRUPTION_PHRASES

    @staticmethod
    def stopping_response() -> str:
        return "Alright, stopping that."

    @staticmethod
    def acknowledgement(intent: str) -> str:
        lookup = {
            "control": "On it, Boss.",
            "news": "Checking that now, Boss.",
            "verification": "Let me verify that, Boss.",
            "chat": "Right here, Boss.",
        }
        return lookup.get(intent, "On it, Boss.")

    @staticmethod
    def soften_uncertainty(text: str) -> str:
        lowered = text.lower()
        if "insufficient verified evidence" in lowered:
            return "Not enough solid proof on that one, Boss."
        if "unsupported or contradicted" in lowered:
            return "That one looks shaky, Boss."
        return text

    @staticmethod
    def polish_response(text: str, *, mode: str = "assistant") -> str:
        cleaned = " ".join((text or "").split())
        if not cleaned:
            return "Still here, Boss."
        if cleaned == FridayPersonality.stopping_response():
            return cleaned
        for filler in FILLER_PHRASES:
            cleaned = cleaned.replace(f"{filler} ", "")
        cleaned = FridayPersonality.soften_uncertainty(cleaned)
        if "boss" not in cleaned.lower():
            if cleaned.endswith((".", "!", "?")):
                cleaned = f"{cleaned[:-1]}, Boss{cleaned[-1]}"
            else:
                cleaned = f"{cleaned}, Boss."
        if mode == "assistant" and len(cleaned) > 180:
            first_sentence = cleaned.split(". ", 1)[0].strip()
            cleaned = (
                first_sentence if first_sentence.endswith(".") else f"{first_sentence}."
            )
        return cleaned

    @staticmethod
    def detect_emotion(text: str) -> Optional[str]:
        """Detect emotion from text content"""
        if not text:
            return None
            
        text_lower = text.lower()
        
        # Check for each emotion category
        for emotion, keywords in EMOTION_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return emotion
        return None

    @staticmethod
    def adapt_response_for_emotion(response: str, emotion: Optional[str]) -> str:
        """Adapt response based on detected emotion"""
        if not emotion:
            return response
            
        # Emotion-specific adaptations
        emotion_adaptations = {
            "frustrated": "I understand this might be frustrating, Boss. Let me try to help clarify things for you.",
            "confused": "No worries, Boss. Let me break this down in a simpler way for you.",
            "excited": "That's great to hear, Boss! Your enthusiasm is contagious!",
            "sad": "I'm here for you, Boss. Let's see if we can work through this together.",
            "grateful": "You're very welcome, Boss. Happy to be of assistance!",
            "urgent": "I understand this is urgent, Boss. Let me prioritize this and get you an answer quickly."
        }
        
        # If we have a specific adaptation for this emotion, prepend it
        if emotion in emotion_adaptations:
            return f"{emotion_adaptations[emotion]} {response}"
        
        return response

    @staticmethod
    def build_news_summary(topic: str, headlines: Iterable[str]) -> str:
        picks = [
            headline.strip() for headline in headlines if headline and headline.strip()
        ]
        if not picks:
            return f"I couldn’t pull anything solid on {topic} just yet, Boss."
        top = picks[:3]
        if len(top) == 1:
            return f"Latest on {topic}: {top[0]}, Boss."
        return f"Latest on {topic}, Boss: " + " | ".join(top)


friday_personality = FridayPersonality()


def get_friday_system_prompt(mode: str = "assistant", context: str = "normal") -> str:
    return friday_personality.get_system_prompt(mode, context)


def adapt_response(response: str, context: str = "normal") -> str:
    mode = "verification" if context == "verification" else "assistant"
    return friday_personality.polish_response(response, mode=mode)


def get_friday_traits() -> dict:
    return friday_personality.TRAITS.copy()
