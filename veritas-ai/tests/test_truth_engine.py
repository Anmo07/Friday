import sys
import os
import pytest

# Ensure our local modules are resolvable by pytest during independent CI checks
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.truth_engine import TruthEngine

def test_source_authority():
    engine = TruthEngine()
    score = engine.calculate_source_authority(["https://www.whitehouse.gov/news", "https://twitter.com/user"])
    # 1.0 (gov) + 0.3 (social) / 2 = 0.65
    assert score == 0.65

def test_full_truth_score():
    engine = TruthEngine()
    data = {
        "sources": ["https://apnews.com/article/1", "https://reuters.com/article/1"],
        "agreeing_sources": 2,
        "conflicting_sources": 0,
        "temporal_anomalies": False,
        "rag_hits": 3,
        "kg_hits": 0,
        "fake_probability": 0.1
    }
    result = engine.compute_truth_score(data)
    
    assert result["breakdown"]["source_authority"] == 0.85
    assert result["breakdown"]["cross_source_agreement"] == 1.0
    assert result["breakdown"]["temporal_consistency"] == 0.9
    assert result["breakdown"]["claim_verifiability"] == 1.0
    assert result["breakdown"]["bias_deviation"] == 0.9
    
    # Expected weighted sum
    # 0.85*0.25 (0.2125) + 1.0*0.25 (0.25) + 0.9*0.15 (0.135) + 1.0*0.20 (0.2) + 0.9*0.15 (0.135) = 0.9325 => rounded to 0.933
    assert result["truth_score"] == 0.933
