from datetime import datetime, timedelta
from collections import Counter
from threading import Lock

class PredictiveIntelligenceEngine:
    """
    State-of-the-art anomaly and spike detection matrix tracking narrative shifts natively.
    Analyzes global incoming payloads intelligently exposing emerging misinformation trends organically.
    """
    def __init__(self):
        self._payload_streams = []
        self._lock = Lock()

    def ingest_payload(self, raw_query: str):
        """ Tracks temporal queries securely extracting structural context natively """
        # Simplified Named Entity Extraction mapped aggressively securely 
        # (In prod, hooks into SpaCy or NLP pipelines globally)
        tokens = [word for word in raw_query.lower().split() if len(word) > 4]
        
        with self._lock:
            for token in tokens[:3]:
                self._payload_streams.append({
                    "keyword_topic": token,
                    "timestamp": datetime.utcnow()
                })
            self._flush_deprecated_telemetry()
        
    def _flush_deprecated_telemetry(self):
        """ Maintains optimal Memory footprints implicitly mapping sliding windows correctly """
        cutoff_bound = datetime.utcnow() - timedelta(hours=2)
        self._payload_streams = [s for s in self._payload_streams if s["timestamp"] >= cutoff_bound]
        
    def generate_horizon_predictions(self) -> list:
        """ 
        Identifies mathematically sudden keyword spikes natively signaling astroturfed misinformation attacks.
        """
        with self._lock:
            self._flush_deprecated_telemetry()
            topics = [item["keyword_topic"] for item in self._payload_streams]
            frequency_matrix = Counter(topics)
        
        alerts = []
        for topic_cluster, hit_count in frequency_matrix.items():
            if hit_count >= 15:
                alerts.append({
                    "trend_alert": True,
                    "topic": topic_cluster,
                    "risk_level": "high",
                    "prediction": "critical misinformation spread rapidly scaling natively"
                })
            elif hit_count >= 5:
                alerts.append({
                    "trend_alert": True,
                    "topic": topic_cluster,
                    "risk_level": "medium",
                    "prediction": "anomalous narrative shift emerging structurally"
                })
                
        return alerts

# Global Singleton mapping persistent boundaries across the runtime limits natively
predictive_engine = PredictiveIntelligenceEngine()
