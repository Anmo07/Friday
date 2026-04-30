import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.firewall import HallucinationFirewall
from models.schemas import QueryResponse, Source

def test_firewall_likely_false():
    fw = HallucinationFirewall(contradiction_threshold=1)
    resp = QueryResponse(
        query="test", summary="test summary", facts=[],
        sources=[], contradictions=["Assertion 1 vs Assertion 2", "Graph Logic Collision"], fake_probability=0.0,
        confidence_score=0.9, truth_score=0.9, timestamp="now"
    )
    res = fw.evaluate(resp)
    assert res.status == "likely_false"

def test_firewall_uncertain():
    fw = HallucinationFirewall()
    # Missing 2 high trusted sources
    resp = QueryResponse(
        query="test", summary="test", facts=[],
        sources=[Source(url="test.com", credibility_score=0.5, type="media")], 
        contradictions=[], fake_probability=0.0,
        confidence_score=0.9, truth_score=0.9, timestamp="now"
    )
    res = fw.evaluate(resp)
    assert res.status == "uncertain"

def test_firewall_verified():
    fw = HallucinationFirewall()
    resp = QueryResponse(
        query="test", summary="test", facts=[],
        sources=[
            Source(url="whitehouse.gov", credibility_score=0.95, type="official"),
            Source(url="harvard.edu", credibility_score=0.95, type="official")
        ], 
        contradictions=[], fake_probability=0.0,
        confidence_score=0.9, truth_score=0.8, timestamp="now"
    )
    res = fw.evaluate(resp)
    assert res.status == "verified"
