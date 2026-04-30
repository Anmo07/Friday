from models.schemas import QueryResponse
import logging


class HallucinationFirewall:
    def __init__(self, contradiction_threshold: int = 1):
        self.contradiction_threshold = contradiction_threshold

    def evaluate(self, payload: QueryResponse) -> QueryResponse:
        trusted_sources = [s for s in payload.sources if s.credibility_score >= 0.75]
        trusted_count = len(trusted_sources)
        contradiction_count = len(payload.contradictions)
        if contradiction_count > self.contradiction_threshold:
            payload.status = "likely_false"
            logging.warning(
                f"Firewall Override (Graph/RAG Contradictions > {self.contradiction_threshold}): Status clamped to {payload.status}"
            )
            return payload
        if trusted_count < 2:
            payload.status = "uncertain"
            logging.warning(
                f"Firewall Override (Trusted Auth Limit < 2): Status clamped to {payload.status}"
            )
            return payload
        if payload.truth_score > 0.75:
            payload.status = "verified"
            return payload
        payload.status = "uncertain"
        return payload
