import pytest

from app.core.assistant import assistant_orchestrator


def test_classify_routes_control_news_and_verification():
    control = assistant_orchestrator.classify("Open VS Code")
    assert control.kind == "control"
    assert control.mode == "assistant"

    news = assistant_orchestrator.classify("Search latest news about AI")
    assert news.kind == "news"
    assert news.mode == "assistant"

    verification = assistant_orchestrator.classify("Verify whether this claim is true")
    assert verification.kind == "verification"
    assert verification.mode == "verification"


@pytest.mark.asyncio
async def test_execute_interrupt_returns_stop_response():
    response = await assistant_orchestrator.execute("stop")

    assert response["intent"] == "interrupt"
    assert response["interrupted"] is True
    assert response["summary"] == "Alright, stopping that."
