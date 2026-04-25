"""
FRIDAY Response Formatting Engine
Formats AI responses into structured, clean output.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum


class TruthScore(Enum):
    """Truth score levels for response validation."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


@dataclass
class FormattedResponse:
    """Structured response format."""
    summary: str
    truth_score: TruthScore
    confidence: float  # 0.0 to 1.0
    key_points: List[str]
    raw_response: Optional[str] = None


class ResponseFormatter:
    """Formats AI responses into structured FRIDAY-style output."""
    
    @staticmethod
    def format_response(
        response: str,
        truth_score: TruthScore = TruthScore.UNKNOWN,
        confidence: float = 0.8,
        key_points: Optional[List[str]] = None
    ) -> FormattedResponse:
        """
        Format response into structured format.
        
        Args:
            response: Raw AI response
            truth_score: Truth score assessment
            confidence: Confidence level (0.0-1.0)
            key_points: Key facts/points from response
            
        Returns:
            FormattedResponse object
        """
        # Extract summary (first 1-2 lines or first sentence)
        summary = ResponseFormatter._extract_summary(response)
        
        # Use provided key points or extract them
        if key_points is None:
            key_points = ResponseFormatter._extract_key_points(response)
        
        return FormattedResponse(
            summary=summary,
            truth_score=truth_score,
            confidence=confidence,
            key_points=key_points,
            raw_response=response
        )
    
    @staticmethod
    def _extract_summary(response: str) -> str:
        """Extract summary from response (1-2 lines)."""
        # Take first sentence or first 200 chars
        sentences = response.split('. ')
        if sentences:
            first_sentence = sentences[0].strip()
            if len(first_sentence) > 200:
                # If first sentence is too long, take first 200 chars
                return first_sentence[:200] + "..."
            return first_sentence
        
        # Fallback: first 200 characters
        return response[:200] + ("..." if len(response) > 200 else "")
    
    @staticmethod
    def _extract_key_points(response: str) -> List[str]:
        """Extract key points from response."""
        # Simple extraction: split by sentences and take meaningful ones
        sentences = [s.strip() for s in response.split('.') if s.strip()]
        
        # Filter for likely key points (contains facts, numbers, or important info)
        key_points = []
        for sentence in sentences[:5]:  # Limit to first 5 sentences
            # Skip very short sentences
            if len(sentence) < 10:
                continue
            # Skip sentences that are likely filler
            if any(filler in sentence.lower() for filler in 
                  ['i think', 'i believe', 'in my opinion', 'you know']):
                continue
            key_points.append(sentence)
        
        # If we didn't get enough points, use first few sentences
        if len(key_points) < 2:
            key_points = [s.strip() for s in sentences[:3] if len(s.strip()) > 10]
        
        return key_points[:4]  # Maximum 4 key points
    
    @staticmethod
    def to_display_format(formatted_response: FormattedResponse) -> str:
        """
        Convert formatted response to display string.
        
        Args:
            formatted_response: FormattedResponse object
            
        Returns:
            Formatted string for display
        """
        lines = [
            f"Summary: {formatted_response.summary}",
            f"Truth Score: {formatted_response.truth_score.value}",
            f"Confidence: {int(formatted_response.confidence * 100)}%",
            "Key Facts:"
        ]
        
        for i, point in enumerate(formatted_response.key_points, 1):
            lines.append(f"- {point}")
        
        return "\n".join(lines)


# Global formatter instance
response_formatter = ResponseFormatter()

def format_friday_response(
    response: str,
    truth_score: TruthScore = TruthScore.UNKNOWN,
    confidence: float = 0.8,
    key_points: Optional[List[str]] = None
) -> FormattedResponse:
    """Format response using FRIDAY formatter."""
    return response_formatter.format_response(response, truth_score, confidence, key_points)

def format_for_display(formatted_response: FormattedResponse) -> str:
    """Format response for display."""
    return response_formatter.to_display_format(formatted_response)