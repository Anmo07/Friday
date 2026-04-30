import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.consensus_engine import ConsensusEngine
from models.schemas import QueryResponse


def test_consensus_calculation():
    engine = ConsensusEngine()
    resp = QueryResponse(
        query="test",
        summary="test",
        facts=[],
        sources=[],
        contradictions=[],
        fake_probability=0.2,
        confidence_score=0.7,
        truth_score=0.9,
        timestamp="now",
    )
    res = engine.evaluate(resp)
    assert res.confidence_score == 0.8
