from models.schemas import QueryResponse


class ConsensusEngine:
    def evaluate(self, payload: QueryResponse) -> QueryResponse:
        llm_confidence = payload.confidence_score
        classifier_confidence = max(0.0, 1.0 - payload.fake_probability)
        rule_confidence = payload.truth_score
        computed_consensus = (
            llm_confidence + classifier_confidence + rule_confidence
        ) / 3.0
        payload.confidence_score = round(computed_consensus, 3)
        return payload
