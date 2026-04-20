from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

class Source(BaseModel):
    url: str
    credibility_score: float = Field(ge=0.0, le=1.0)
    type: Literal["official", "media", "social", "unknown"] = Field(description="official | media | social | unknown")

class QueryRequest(BaseModel):
    query: str = Field(..., description="User query")
    deep: bool = Field(default=False, description="If true, run the full deep analysis pipeline")

class QueryResponse(BaseModel):
    query: str
    summary: str
    facts: List[str] = Field(default_factory=list)
    sources: List[Source] = Field(default_factory=list)
    contradictions: List[str] = Field(default_factory=list)
    fake_probability: float = Field(ge=0.0, le=1.0, default=0.5)
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.0)
    truth_score: float = Field(ge=0.0, le=1.0, default=0.0)
    status: Literal["verified", "likely_false", "uncertain"] = "uncertain"
    explanation: Optional[Dict[str, Any]] = None
    timestamp: str


class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded"]
    service: str
    version: str


class FeedbackResponse(BaseModel):
    status: Literal["success", "error", "no_updates"]
    tracking_stage: Optional[str] = None
    message: Optional[str] = None


class AlertItem(BaseModel):
    alert_type: str
    severity: Literal["low", "medium", "high"]
    message: str
    timestamp: str


class AlertsResponse(BaseModel):
    status: Literal["success"]
    active_global_anomalies: List[AlertItem] = Field(default_factory=list)


class PredictiveAlert(BaseModel):
    trend_alert: bool
    topic: str
    risk_level: Literal["medium", "high"]
    prediction: str


class PredictiveTrendsResponse(BaseModel):
    status: Literal["success"]
    timestamp_horizon: str
    predictive_alerts: List[PredictiveAlert] = Field(default_factory=list)


class StreamAuthorizationResponse(BaseModel):
    status: Literal["stream_authorized"]
    tunnel_socket_uri: str
    query_linked: str


class HistoryEntry(BaseModel):
    id: int
    timestamp: str
    query: str
    status: str
    truth_score: float = Field(ge=0.0, le=1.0)
    summary: str


class HistoryResponse(BaseModel):
    status: Literal["success"]
    items: List[HistoryEntry] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    status: Literal["error"] = "error"
    message: str
