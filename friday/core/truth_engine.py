from typing import List, Dict, Any


class TruthEngine:
    def __init__(self):
        self.weights = {
            "source_authority": 0.25,
            "cross_source_agreement": 0.25,
            "temporal_consistency": 0.15,
            "claim_verifiability": 0.20,
            "bias_deviation": 0.15,
        }

    def calculate_source_authority(self, sources: List[str]) -> float:
        if not sources:
            return 0.5
        scores = []
        for src in sources:
            src_lower = src.lower()
            if any(tld in src_lower for tld in [".gov", ".edu", ".mil", ".int"]):
                scores.append(1.0)
            elif any(
                domain in src_lower
                for domain in [
                    "reuters.com",
                    "apnews.com",
                    "bbc.com",
                    "npr.org",
                    "bloomberg.com",
                ]
            ):
                scores.append(0.85)
            elif any(
                domain in src_lower
                for domain in [
                    "twitter.com",
                    "x.com",
                    "facebook.com",
                    "reddit.com",
                    "tiktok.com",
                    "instagram.com",
                ]
            ):
                scores.append(0.3)
            else:
                scores.append(0.5)
        return sum(scores) / len(scores)

    def calculate_cross_source_agreement(
        self, agreeing_count: int, conflicting_count: int
    ) -> float:
        total = agreeing_count + conflicting_count
        if total == 0:
            return 0.5
        return agreeing_count / total

    def calculate_temporal_consistency(self, anomalies_detected: bool) -> float:
        return 0.3 if anomalies_detected else 0.9

    def calculate_claim_verifiability(
        self, vector_similarity: float = 0.0, graph_connectivity: float = 0.0
    ) -> float:
        VECTOR_WEIGHT = 0.4
        GRAPH_WEIGHT = 0.6
        fusion_score = (vector_similarity * VECTOR_WEIGHT) + (
            graph_connectivity * GRAPH_WEIGHT
        )
        if fusion_score >= 0.85:
            return 1.0
        elif fusion_score >= 0.65:
            return 0.8
        elif fusion_score >= 0.4:
            return 0.5
        else:
            return 0.2

    def calculate_bias_deviation(self, fake_news_probability: float) -> float:
        return max(0.0, 1.0 - fake_news_probability)

    def compute_truth_score(self, data: Dict[str, Any]) -> Dict[str, Any]:
        auth_score = self.calculate_source_authority(data.get("sources", []))
        agreement_score = self.calculate_cross_source_agreement(
            data.get("agreeing_sources", 0), data.get("conflicting_sources", 0)
        )
        temporal_score = self.calculate_temporal_consistency(
            data.get("temporal_anomalies", False)
        )
        verifiability_score = self.calculate_claim_verifiability(
            vector_similarity=data.get("vector_similarity", 0.0),
            graph_connectivity=data.get("graph_connectivity", 0.0),
        )
        bias_score = self.calculate_bias_deviation(data.get("fake_probability", 0.0))
        final_score = (
            auth_score * self.weights["source_authority"]
            + agreement_score * self.weights["cross_source_agreement"]
            + temporal_score * self.weights["temporal_consistency"]
            + verifiability_score * self.weights["claim_verifiability"]
            + bias_score * self.weights["bias_deviation"]
        )
        breakdown = {
            "source_authority": round(auth_score, 3),
            "cross_source_agreement": round(agreement_score, 3),
            "temporal_consistency": round(temporal_score, 3),
            "claim_verifiability": round(verifiability_score, 3),
            "bias_deviation": round(bias_score, 3),
        }
        try:
            from core.observability import observability

            observability.log_truth_score(round(final_score, 3), breakdown)
        except ImportError:
            pass
        return {"truth_score": round(final_score, 3), "breakdown": breakdown}

    def detect_misinformation_in_history(self, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Scan history for claims with low truth scores and flag them as misinformation alerts"""
        alerts = []
        for exchange in history:
            # If we have a truth score from a previous analysis
            if "truth_score" in exchange and exchange["truth_score"] < 0.6:
                alerts.append({
                    "timestamp": exchange.get("timestamp"),
                    "query": exchange.get("query"),
                    "warning": f"Boss, I noticed a previous claim about '{exchange.get('query')[:50]}...' might be inaccurate based on my latest data.",
                    "score": exchange["truth_score"]
                })
        return alerts
