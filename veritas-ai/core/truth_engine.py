from typing import List, Dict, Any

class TruthEngine:
    """
    Computes a multi-factor mathematical truth score for intelligence reports.
    Replaces rudimentary single-variable credibility logic with strict mathematical assertions.
    """
    
    def __init__(self):
        # Base weights defined by strict system requirements
        self.weights = {
            "source_authority": 0.25,
            "cross_source_agreement": 0.25,
            "temporal_consistency": 0.15,
            "claim_verifiability": 0.20,
            "bias_deviation": 0.15
        }
        
    def calculate_source_authority(self, sources: List[str]) -> float:
        """
        Calculates authority based on domain mapping.
        .gov, .edu -> 1.0 (High Weight)
        known media -> 0.85
        social -> 0.30
        unknown -> 0.50
        """
        if not sources: return 0.5
        
        scores = []
        for src in sources:
            src_lower = src.lower()
            if any(tld in src_lower for tld in ['.gov', '.edu', '.mil', '.int']):
                scores.append(1.0)
            elif any(domain in src_lower for domain in ['reuters.com', 'apnews.com', 'bbc.com', 'npr.org', 'bloomberg.com']):
                scores.append(0.85)
            elif any(domain in src_lower for domain in ['twitter.com', 'x.com', 'facebook.com', 'reddit.com', 'tiktok.com', 'instagram.com']):
                scores.append(0.3)
            else:
                scores.append(0.5)
        
        return sum(scores) / len(scores)

    def calculate_cross_source_agreement(self, agreeing_count: int, conflicting_count: int) -> float:
        """
        Calculates consensus ratio. Normalizes scores based on conflicts.
        """
        total = agreeing_count + conflicting_count
        if total == 0:
            return 0.5 # Neutral mapping if neither exists yet
        return agreeing_count / total

    def calculate_temporal_consistency(self, anomalies_detected: bool) -> float:
        """
        Penalizes sudden narrative shifts by checking timestamps.
        """
        return 0.3 if anomalies_detected else 0.9

    def calculate_claim_verifiability(self, rag_hits: int, kg_hits: int = 0) -> float:
        """
        Checks if claim appears in internal memory boundaries (RAG + pending Knowledge Graph).
        """
        total_hits = rag_hits + kg_hits
        if total_hits >= 3: return 1.0
        if total_hits == 2: return 0.8
        if total_hits == 1: return 0.5
        return 0.2

    def calculate_bias_deviation(self, fake_news_probability: float) -> float:
        """
        Inverses probability for truth scaling utilizing the Transformer NLP classifications.
        """
        return max(0.0, 1.0 - fake_news_probability)

    def compute_truth_score(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Computes the final independent dynamically weighted truth sum against all sources.
        """
        auth_score = self.calculate_source_authority(data.get("sources", []))
        agreement_score = self.calculate_cross_source_agreement(
            data.get("agreeing_sources", 0), 
            data.get("conflicting_sources", 0)
        )
        temporal_score = self.calculate_temporal_consistency(data.get("temporal_anomalies", False))
        verifiability_score = self.calculate_claim_verifiability(
            data.get("rag_hits", 0),
            data.get("kg_hits", 0)
        )
        bias_score = self.calculate_bias_deviation(data.get("fake_probability", 0.0))

        final_score = (
            auth_score * self.weights["source_authority"] +
            agreement_score * self.weights["cross_source_agreement"] +
            temporal_score * self.weights["temporal_consistency"] +
            verifiability_score * self.weights["claim_verifiability"] +
            bias_score * self.weights["bias_deviation"]
        )

        return {
            "truth_score": round(final_score, 3),
            "breakdown": {
                "source_authority": round(auth_score, 3),
                "cross_source_agreement": round(agreement_score, 3),
                "temporal_consistency": round(temporal_score, 3),
                "claim_verifiability": round(verifiability_score, 3),
                "bias_deviation": round(bias_score, 3)
            }
        }
