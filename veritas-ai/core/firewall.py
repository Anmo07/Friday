from models.schemas import QueryResponse
import logging

class HallucinationFirewall:
    """
    Evaluates final intelligence pipelines via deterministic rule matrices effectively stopping
    LLM hallucinations or unverified claims from passing into the structural API boundaries natively.
    """
    
    def __init__(self, contradiction_threshold: int = 1):
        self.contradiction_threshold = contradiction_threshold
        
    def evaluate(self, payload: QueryResponse) -> QueryResponse:
        """
        Executes strictly unyielding heuristic validation bounds mapping:
        - If trusted_sources < 2 → status = 'uncertain'
        - If contradiction_score > threshold → status = 'likely_false'
        - If truth_score > 0.75 → status = 'verified'
        """
        
        # Calculate isolated reliable source clusters (score must be exactly high confidence)
        trusted_sources = [s for s in payload.sources if s.credibility_score >= 0.75]
        trusted_count = len(trusted_sources)
        
        contradiction_count = len(payload.contradictions)
        
        # Override 1: Explicit Logic Constraints
        if contradiction_count > self.contradiction_threshold:
            payload.status = "likely_false"
            logging.warning(f"Firewall Override (Graph/RAG Contradictions > {self.contradiction_threshold}): Status clamped to {payload.status}")
            return payload
            
        # Override 2: Sourcing Authority
        if trusted_count < 2:
            payload.status = "uncertain"
            logging.warning(f"Firewall Override (Trusted Auth Limit < 2): Status clamped to {payload.status}")
            return payload
            
        # Override 3: Verification Array
        if payload.truth_score > 0.75:
            payload.status = "verified"
            return payload
            
        # Catchall baseline
        payload.status = "uncertain"
        return payload
