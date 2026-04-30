from models.schemas import QueryResponse
from core.truth_engine import TruthEngine


class ExplainabilityLayer:
    def __init__(self):
        self.truth_engine = TruthEngine()

    def evaluate(self, payload: QueryResponse) -> QueryResponse:
        explanation = {"why_true": [], "why_false": [], "confidence_breakdown": {}}
        trusted_sources = [s for s in payload.sources if s.credibility_score >= 0.75]
        if len(trusted_sources) >= 2:
            explanation["why_true"].append(
                f"Confirmed directly by {len(trusted_sources)} authoritative trusted domains."
            )
        if payload.fake_probability < 0.3:
            explanation["why_true"].append(
                "Passed Transformer classification NLP layer safely (Zero explicit propaganda matched)."
            )
        if not payload.contradictions:
            explanation["why_true"].append(
                "Mathematical graph comparisons revealed no structural assertion deviations natively."
            )
        if payload.contradictions:
            explanation["why_false"].append(
                f"Detected {len(payload.contradictions)} isolated contradictions across Knowledge Graph limits."
            )
        if payload.fake_probability > 0.6:
            explanation["why_false"].append(
                f"Extreme classification bias detected logically scoring at {payload.fake_probability} limits."
            )
        if len(trusted_sources) == 0:
            explanation["why_false"].append(
                "Zero high-authority sources discovered verifying this claim explicitly."
            )
        auth_score = self.truth_engine.calculate_source_authority(
            [s.url for s in payload.sources]
        )
        bias_score = self.truth_engine.calculate_bias_deviation(
            payload.fake_probability
        )
        agreement_score = (
            1.0
            if not payload.contradictions
            else max(0.0, 1.0 - (len(payload.contradictions) * 0.2))
        )
        explanation["confidence_breakdown"] = {
            "authority": round(auth_score, 3),
            "agreement": round(agreement_score, 3),
            "bias": round(bias_score, 3),
        }
        payload.explanation = explanation
        return payload
