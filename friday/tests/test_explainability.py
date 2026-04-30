import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.explainability_layer import ExplainabilityLayer
from models.schemas import QueryResponse, Source


def test_explainability_logic_generation():
    explainer = ExplainabilityLayer()
    resp = QueryResponse(
        query="Test logic arrays explicitly.",
        summary="Test",
        facts=[],
        sources=[Source(url="test.edu", credibility_score=0.9, type="official")],
        contradictions=["Sample Contradiction detected."],
        fake_probability=0.2,
        confidence_score=0.9,
        truth_score=0.8,
        timestamp="Now",
    )
    evaluated = explainer.evaluate(resp)
    assert evaluated.explanation is not None
    assert "why_true" in evaluated.explanation
    assert "why_false" in evaluated.explanation
    assert any(
        "Passed Transformer classification" in fact
        for fact in evaluated.explanation["why_true"]
    )
    assert any(
        "Detected 1 isolated contradictions" in fact
        for fact in evaluated.explanation["why_false"]
    )
    assert evaluated.explanation["confidence_breakdown"]["authority"] == 1.0
