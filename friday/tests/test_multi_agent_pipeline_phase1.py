import asyncio
import os
import sys
import time
import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
pytest.importorskip("crewai")
from pipelines import multi_agent_pipeline as pipeline


class _DummyAgents:
    def verification_agent(self, tools):
        return object()

    def fact_checking_agent(self, tools):
        return object()

    def misinformation_agent(self, tools):
        return object()


@pytest.mark.asyncio
async def test_parallel_validation_runs_concurrently(monkeypatch):
    async def fake_run_validation_agent(**kwargs):
        await asyncio.sleep(0.10)
        return kwargs["agent_name"]

    monkeypatch.setattr(pipeline, "_run_validation_agent", fake_run_validation_agent)
    start = time.perf_counter()
    result = await pipeline._run_parallel_validation(
        agents=_DummyAgents(),
        query="Is this claim true?",
        raw_report="Synthetic report for concurrency validation.",
    )
    elapsed = time.perf_counter() - start
    assert elapsed < 0.22
    assert result["verification_result"] == "Verification Agent"
    assert result["fact_check_result"] == "Fact Checker"
    assert result["misinformation_result"] == "Misinformation Analyzer"
