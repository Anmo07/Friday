import json
import os
from datetime import datetime, timezone
from typing import Dict, Any

class ObservabilityLayer:
    """
    Monitors AI model behavior, tracks performance metrics, 
    and detects drift for truth scores over time.
    """
    def __init__(self, log_dir="logs"):
        # Absolute path based on the core directory relative path to ensure logs goes in veritas-ai/logs
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.log_dir = os.path.join(base_path, log_dir)
        os.makedirs(self.log_dir, exist_ok=True)
        
        self.metrics_file = os.path.join(self.log_dir, "observability_metrics.json")
        self.drift_file = os.path.join(self.log_dir, "drift_logs.json")
        
        # In-memory history for drift calculation (simple moving average over last 10 scores)
        self.truth_score_history = []
        self.window_size = 10
        self.drift_threshold = 0.2  # 20% deviation from moving average triggers a drift alert

    def _append_to_jsonl(self, file_path: str, data: Dict[str, Any]):
        """Appends a JSON record as a new line in a thread-safe-ish manner."""
        try:
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(data) + "\n")
        except Exception as e:
            print(f"Observability logging error: {e}")

    def log_llm_metrics(self, latency: float, prompt_tokens: int, completion_tokens: int, confidence: float = None):
        """Logs model performance metrics during inference."""
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "llm_inference",
            "latency_seconds": round(latency, 4),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "confidence_score": confidence
        }
        self._append_to_jsonl(self.metrics_file, record)

    def log_truth_score(self, truth_score: float, breakdown: Dict[str, float]):
        """Logs truth score and detects statistical drift against moving average."""
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "truth_computation",
            "truth_score": truth_score,
            "breakdown": breakdown
        }
        self._append_to_jsonl(self.metrics_file, record)

        # Drift detection logic
        if len(self.truth_score_history) >= self.window_size:
            moving_avg = sum(self.truth_score_history[-self.window_size:]) / self.window_size
            deviation = abs(truth_score - moving_avg)
            
            if deviation > self.drift_threshold:
                drift_record = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "event": "truth_score_drift_detected",
                    "current_score": truth_score,
                    "moving_average": round(moving_avg, 3),
                    "deviation": round(deviation, 3),
                    "threshold": self.drift_threshold
                }
                self._append_to_jsonl(self.drift_file, drift_record)
        
        self.truth_score_history.append(truth_score)

# Global instance
observability = ObservabilityLayer()
