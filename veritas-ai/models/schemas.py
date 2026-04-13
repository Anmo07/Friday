from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class Source(BaseModel):
    url: str
    credibility_score: float
    type: str = Field(description="official | media | social | unknown")

class QueryResponse(BaseModel):
    query: str
    summary: str
    facts: List[str]
    sources: List[Source]
    contradictions: List[str]
    fake_probability: float
    confidence_score: float
    truth_score: float = 0.0
    status: str = "uncertain"
    explanation: Optional[Dict[str, Any]] = None
    timestamp: str
