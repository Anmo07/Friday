import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipelines.response_builder import build_query_response


def test_response_builder_extracts_sources_and_scores():
    report = """
    Reuters confirmed the update in a published report [https://www.reuters.com/world/example-story].
    Classified Label: FAKE | NLP Confidence: 0.20
    No direct contradiction was found in the current evidence set.
    """

    response = build_query_response("Example claim", report)

    assert response.query == "Example claim"
    assert response.sources
    assert response.sources[0].type == "media"
    assert response.fake_probability == 0.2
    assert 0.0 <= response.truth_score <= 1.0


def test_response_builder_rejects_placeholder_sources():
    report = "Simulated result [https://example.com/1]. No configured news providers are available for this environment."
    response = build_query_response("Placeholder claim", report)

    assert response.sources == []
    assert response.status == "uncertain"
    assert "Insufficient verified evidence" in response.summary
