import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.consensus_engine import ConsensusEngine
from models.schemas import QueryResponse

def test_consensus_calculation():
    engine = ConsensusEngine()
    resp = QueryResponse(
        query="test", summary="test", facts=[], sources=[], contradictions=[],
        fake_probability=0.2,   # classifier_confidence will inherently become 0.8
        confidence_score=0.7,   # baseline LLM metric
        truth_score=0.9,        # phase 10 logic metric
        timestamp="now"
    )
    
    res = engine.evaluate(resp)
    # Expected: (0.7 + 0.8 + 0.9) / 3 = 2.4 / 3 = 0.80
    assert res.confidence_score == 0.8
