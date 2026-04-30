import asyncio
import pytest
from core.pipeline import FridayPipeline
from unittest.mock import MagicMock, AsyncMock

@pytest.mark.asyncio
async def test_pipeline_classification():
    pipeline = FridayPipeline()
    assert pipeline.classify("open the terminal") == "tier_1_fast"
    assert pipeline.classify("what is the capital of France") == "tier_2_standard"
    assert pipeline.classify("investigate the financial report") == "tier_3_deep"

@pytest.mark.asyncio
async def test_pipeline_stream_run_mocked(monkeypatch):
    pipeline = FridayPipeline()
    
    # Mock _stream_ollama to return a fixed sequence
    async def mock_stream(prompt, model):
        yield "Hello"
        yield " world"
    
    monkeypatch.setattr(pipeline, "_stream_ollama", mock_stream)
    
    # Mock resolve_model_name to avoid actual model resolution
    monkeypatch.setattr("models.ollama_runtime.resolve_model_name", lambda x: "mock-model")
    
    tokens = []
    async for chunk in pipeline.stream_run("hi"):
        if "event: token" in chunk:
            import json
            data = json.loads(chunk.split("data: ")[1])
            tokens.append(data["t"])
            
    assert "".join(tokens) == "Hello world"

@pytest.mark.asyncio
async def test_reciprocal_rank_fusion():
    pipeline = FridayPipeline()
    vector_results = [{"id": "doc1"}, {"id": "doc2"}]
    graph_results = [{"id": "doc2"}, {"id": "doc3"}]
    
    fused = pipeline.reciprocal_rank_fusion(vector_results, graph_results)
    # doc2 appears in both, so it should have higher score
    assert fused[0][0] == "doc2"
