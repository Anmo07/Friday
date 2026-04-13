from pydantic import BaseModel, Field
from typing import List

class Source(BaseModel):
    url: str
    credibility_score: float
    type: str = Field(description="official | media | social")

class QueryResponse(BaseModel):
    query: str
    summary: str
    facts: List[str]
    sources: List[Source]
    contradictions: List[str]
    fake_probability: float
    confidence_score: float
    timestamp: str
