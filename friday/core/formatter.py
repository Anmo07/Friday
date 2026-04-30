from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum


class TruthScore(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


@dataclass
class FormattedResponse:
    summary: str
    truth_score: TruthScore
    confidence: float
    key_points: List[str]
    raw_response: Optional[str] = None


class ResponseFormatter:
    @staticmethod
    def format_response(
        response: str,
        truth_score: TruthScore = TruthScore.UNKNOWN,
        confidence: float = 0.8,
        key_points: Optional[List[str]] = None,
    ) -> FormattedResponse:
        summary = ResponseFormatter._extract_summary(response)
        if key_points is None:
            key_points = ResponseFormatter._extract_key_points(response)
        return FormattedResponse(
            summary=summary,
            truth_score=truth_score,
            confidence=confidence,
            key_points=key_points,
            raw_response=response,
        )

    @staticmethod
    def _extract_summary(response: str) -> str:
        sentences = response.split(". ")
        if sentences:
            first_sentence = sentences[0].strip()
            if len(first_sentence) > 200:
                return first_sentence[:200] + "..."
            return first_sentence
        return response[:200] + ("..." if len(response) > 200 else "")

    @staticmethod
    def _extract_key_points(response: str) -> List[str]:
        sentences = [s.strip() for s in response.split(".") if s.strip()]
        key_points = []
        for sentence in sentences[:5]:
            if len(sentence) < 10:
                continue
            if any(
                filler in sentence.lower()
                for filler in ["i think", "i believe", "in my opinion", "you know"]
            ):
                continue
            key_points.append(sentence)
        if len(key_points) < 2:
            key_points = [s.strip() for s in sentences[:3] if len(s.strip()) > 10]
        return key_points[:4]

    @staticmethod
    def to_display_format(formatted_response: FormattedResponse) -> str:
        lines = [
            f"Summary: {formatted_response.summary}",
            f"Truth Score: {formatted_response.truth_score.value}",
            f"Confidence: {int(formatted_response.confidence * 100)}%",
            "Key Facts:",
        ]
        for i, point in enumerate(formatted_response.key_points, 1):
            lines.append(f"- {point}")
        return "\n".join(lines)


response_formatter = ResponseFormatter()


def format_friday_response(
    response: str,
    truth_score: TruthScore = TruthScore.UNKNOWN,
    confidence: float = 0.8,
    key_points: Optional[List[str]] = None,
) -> FormattedResponse:
    return response_formatter.format_response(
        response, truth_score, confidence, key_points
    )


def format_for_display(formatted_response: FormattedResponse) -> str:
    return response_formatter.to_display_format(formatted_response)
