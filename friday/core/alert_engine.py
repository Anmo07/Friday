from collections import deque
from datetime import datetime
from typing import Dict, List
from app.core.config import settings
from models.schemas import QueryResponse

_recent_alerts: deque[Dict] = deque(maxlen=settings.ALERTS_MAX_ITEMS)


def record_alerts(alerts: List[Dict]) -> None:
    for alert in alerts:
        _recent_alerts.appendleft(alert)


def get_recent_alerts(limit: int = 20) -> List[Dict]:
    return list(_recent_alerts)[:limit]


class AlertEngine:
    def evaluate(self, payload: QueryResponse) -> List[Dict]:
        alerts = []
        if len(payload.contradictions) >= 2:
            alerts.append(
                {
                    "alert_type": "contradiction",
                    "severity": "high",
                    "message": f"Critical logical contradiction count breached thresholds explicitly ({len(payload.contradictions)} instances).",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                }
            )
        if payload.fake_probability > 0.7:
            alerts.append(
                {
                    "alert_type": "fake_news",
                    "severity": "high",
                    "message": f"Transformer explicitly mapped propaganda elements strictly scaling {payload.fake_probability} index thresholds.",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                }
            )
        if payload.truth_score < 0.4:
            alerts.append(
                {
                    "alert_type": "anomaly",
                    "severity": "medium",
                    "message": f"Severe loss of baseline reality confidence natively scoring at {payload.truth_score}.",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                }
            )
        summary_lower = payload.summary.lower()
        if (
            "breaking" in summary_lower
            or "urgent" in summary_lower
            or "alert" in summary_lower
        ):
            alerts.append(
                {
                    "alert_type": "anomaly",
                    "severity": "low",
                    "message": "High priority temporal anomaly detected within active text parsing (Breaking News).",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                }
            )
        return alerts
