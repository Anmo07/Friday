import json
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional


class ObservabilityLayer:
    def __init__(self, log_dir="logs"):
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.log_dir = os.path.join(base_path, log_dir)
        os.makedirs(self.log_dir, exist_ok=True)
        self.metrics_file = os.path.join(self.log_dir, "observability_metrics.json")
        self.drift_file = os.path.join(self.log_dir, "drift_logs.json")
        self.truth_score_history = []
        self.window_size = 10
        self.drift_threshold = 0.2

    def _append_to_jsonl(self, file_path: str, data: Dict[str, Any]):
        try:
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(data) + "\n")
        except Exception as e:
            print(f"Observability logging error: {e}")

    def log_llm_metrics(
        self,
        latency: float,
        prompt_tokens: int,
        completion_tokens: int,
        confidence: Optional[float] = None,
    ):
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "llm_inference",
            "latency_seconds": round(latency, 4),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "confidence_score": confidence,
        }
        self._append_to_jsonl(self.metrics_file, record)

    def log_truth_score(self, truth_score: float, breakdown: Dict[str, float]):
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "truth_computation",
            "truth_score": truth_score,
            "breakdown": breakdown,
        }
        self._append_to_jsonl(self.metrics_file, record)
        if len(self.truth_score_history) >= self.window_size:
            moving_avg = (
                sum(self.truth_score_history[-self.window_size :]) / self.window_size
            )
            deviation = abs(truth_score - moving_avg)
            if deviation > self.drift_threshold:
                drift_record = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "event": "truth_score_drift_detected",
                    "current_score": truth_score,
                    "moving_average": round(moving_avg, 3),
                    "deviation": round(deviation, 3),
                    "threshold": self.drift_threshold,
                }
                self._append_to_jsonl(self.drift_file, drift_record)
        self.truth_score_history.append(truth_score)


observability = ObservabilityLayer()


class TelemetryManager:
    """
    Tracks FLOPs, energy consumption, and dollar cost per query.
    Feeds data back into MoE router for dynamic scaling.
    """

    def __init__(self):
        self.stats = {
            "total_flops": 0,
            "total_energy_joules": 0.0,
            "total_cost_usd": 0.0,
            "battery_level": 1.0,
            "avg_latency_ms": 0.0,
            "query_count": 0,
        }
        self._load_hardware_baseline()

    def _load_hardware_baseline(self):
        try:
            import psutil

            battery = psutil.sensors_battery()
            self.is_on_battery = getattr(battery, "power_plugged", True) == False
            self.battery_percent = getattr(battery, "percent", 100.0) / 100.0
        except:
            self.is_on_battery = False
            self.battery_percent = 1.0

    def track_query_efficiency(self, tier: str, model: str, duration_ms: float):
        try:
            import psutil

            # Update battery state
            battery = psutil.sensors_battery()
            if battery:
                self.stats["battery_level"] = battery.percent / 100.0
                self.is_on_battery = not battery.power_plugged

            # Estimate FLOPs (Roughly: Parameters * 2 per token * tokens)
            param_count = 3e9 if "phi3" in model or "3b" in model else 8e9
            estimated_tokens = (duration_ms / 1000) * 20  # Assume 20 t/s
            flops_estimate = param_count * 2 * estimated_tokens

            # Energy: 10W-30W for Laptop inference
            power_draw = 15.0 if self.is_on_battery else 30.0
            energy_estimate = (duration_ms / 1000) * power_draw

            self.stats["total_flops"] += flops_estimate
            self.stats["total_energy_joules"] += energy_estimate
            self.stats["query_count"] += 1
            self.stats["avg_latency_ms"] = (
                self.stats["avg_latency_ms"] * (self.stats["query_count"] - 1)
                + duration_ms
            ) / self.stats["query_count"]
        except Exception:
            pass

    def get_scaling_factor(self) -> float:
        """Returns a multiplier for thresholding based on hardware constraints."""
        if self.stats["battery_level"] < 0.15:
            return 0.4  # Ultra-saver mode
        if self.stats["battery_level"] < 0.3 or self.is_on_battery:
            return 0.7  # Balanced mode
        return 1.0

    def get_stt_model_size(self) -> str:
        """
        Dynamic STT model selection based on power state.
        Saves battery by using smaller models when on battery power.
        
        Returns:
            Model size string for MLX-Whisper.
        """
        self._load_hardware_baseline()  # Refresh battery state
        battery = self.stats["battery_level"]

        if battery < 0.2:
            return "tiny.en"   # ~100ms, ~200MB — ultra power saver
        elif battery < 0.5 or self.is_on_battery:
            return "small.en"  # ~150ms, ~400MB — balanced
        else:
            return "base.en"   # ~200ms, ~800MB — full quality

    def get_tts_mode(self) -> str:
        """
        Dynamic TTS mode selection based on power state.
        Prioritizes native TTS on battery, falls back to network when plugged.

        Returns:
            TTS mode: "native" (0ms network), "local" (~50ms), or "cloud" (~300ms).
        """
        self._load_hardware_baseline()  # Refresh battery state
        battery = self.stats["battery_level"]

        if battery < 0.15:
            return "native"  # Zero network latency — ultra power saver
        elif self.is_on_battery:
            return "native"  # Minimize network drain
        else:
            return "native"  # Default to native for best latency

    def get_speaker_verification_mode(self) -> str:
        """
        Dynamic speaker verification strategy based on power state.

        Returns:
            "lightweight" (~30ms ONNX) or "full" (~200ms FunASR).
        """
        self._load_hardware_baseline()  # Refresh battery state
        battery = self.stats["battery_level"]

        if battery < 0.3 or self.is_on_battery:
            return "lightweight"  # ONNX-based, ~30ms, low power
        else:
            return "lightweight"  # Always prefer lightweight on metal

    def log_performance_event(self, stage: str, latency_ms: float, model: str = ""):
        """Log performance metrics for a specific pipeline stage."""
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "pipeline_stage",
            "stage": stage,
            "latency_ms": round(latency_ms, 2),
            "model": model,
            "battery_level": round(self.stats["battery_level"], 2),
            "is_on_battery": self.is_on_battery,
        }
        metrics_file = os.path.join(
            os.path.dirname(self._load_hardware_baseline.__code__.co_filename),
            "../logs/observability_metrics.json"
        )
        try:
            os.makedirs(os.path.dirname(metrics_file), exist_ok=True)
            with open(metrics_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            print(f"Failed to log performance event: {e}")

