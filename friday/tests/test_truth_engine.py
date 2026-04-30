import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.truth_engine import TruthEngine


def test_source_authority():
    engine = TruthEngine()
    score = engine.calculate_source_authority(
        ["https://www.whitehouse.gov/news", "https://twitter.com/user"]
    )
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
        "fake_probability": 0.1,
    }
    result = engine.compute_truth_score(data)
    assert result["breakdown"]["source_authority"] == 0.85
    assert result["breakdown"]["cross_source_agreement"] == 1.0
    assert result["breakdown"]["temporal_consistency"] == 0.9
    assert result["breakdown"]["claim_verifiability"] == 1.0
    assert result["breakdown"]["bias_deviation"] == 0.9
    assert result["truth_score"] == 0.933
