from models.schemas import QueryResponse

class ConsensusEngine:
    """
    Phase 15 Multi-model calculation unifying three disparate architecture layers seamlessly.
    Merges inference parameters (LLM), ML tensor margins (Transformers), and objective Rule variables safely.
    """
    def evaluate(self, payload: QueryResponse) -> QueryResponse:
        
        # 1. LLM Raw Inference Extracted Baseline
        llm_confidence = payload.confidence_score
        
        # 2. Classifier Validation mapped dynamically inverted from the fake news models natively
        classifier_confidence = max(0.0, 1.0 - payload.fake_probability)
        
        # 3. Deterministic Logical Pipeline Metrics dynamically structured via Truth layers
        rule_confidence = payload.truth_score
        
        # Core Average Unifying Consensus Limits
        computed_consensus = (llm_confidence + classifier_confidence + rule_confidence) / 3.0
        
        # Map back over the original LLM guessed outputs safely creating deterministic consensus bounds
        payload.confidence_score = round(computed_consensus, 3)
        
        return payload
