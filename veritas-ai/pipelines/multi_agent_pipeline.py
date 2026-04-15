import asyncio
import logging
import uuid
from contextlib import suppress
from datetime import datetime
from typing import Dict, List

from crewai import Crew, Process, Task

from agents.veritas_agents import VeritasAgents
from config.settings import settings
from core.alert_engine import AlertEngine, record_alerts
from core.consensus_engine import ConsensusEngine
from core.explainability_layer import ExplainabilityLayer
from core.firewall import HallucinationFirewall
from models.schemas import QueryResponse
from pipelines.event_bus import event_bus
from pipelines.response_builder import build_query_response
from tools.kg_tools import kg_build_tool, kg_validate_tool
from tools.news_api import news_search_tool
from tools.nlp_tools import fake_news_detector_tool
from tools.rss_reader import rss_reader_tool
from tools.truth_tools import truth_scoring_tool
from tools.verification_tools import domain_credibility_tool, rag_fact_check_tool
from tools.web_scraper import web_scrape_tool


class PipelineError(RuntimeError):
    """Raised when a pipeline session cannot complete safely."""


_consumer_tasks: List[asyncio.Task] = []
_inflight_queries: Dict[str, asyncio.Future] = {}


async def _run_crew(crew: Crew, timeout_seconds: int) -> str:
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(crew.kickoff),
            timeout=timeout_seconds,
        )
    except asyncio.TimeoutError as exc:
        raise PipelineError("The agent pipeline timed out before it could complete.") from exc
    except Exception as exc:
        raise PipelineError(str(exc)) from exc


def _fallback_response(query: str, message: str) -> QueryResponse:
    return QueryResponse(
        query=query,
        summary=message,
        facts=[],
        sources=[],
        contradictions=[],
        fake_probability=0.5,
        confidence_score=0.0,
        truth_score=0.0,
        status="uncertain",
        timestamp=datetime.utcnow().isoformat() + "Z",
    )


async def verification_consumer_node() -> None:
    agents = VeritasAgents()
    verifier = agents.verification_agent([domain_credibility_tool])

    async for event in event_bus.subscribe("verification_stream"):
        payload = event["payload"]
        session_id = payload["session_id"]
        try:
            task = Task(
                description=(
                    "Take the raw report. Extract all URLs and run them through the Domain Credibility "
                    "Evaluator tool. Attach a credibility score and source type directly to each URL/source "
                    f"in the report.\n\nRAW REPORT:\n{payload['report']}"
                ),
                expected_output="An updated report with explicit source validation notes.",
                agent=verifier,
            )
            crew = Crew(agents=[verifier], tasks=[task], verbose=False)
            result = await _run_crew(crew, settings.AGENT_TASK_TIMEOUT_SECONDS)
            await event_bus.publish(
                "fact_check_stream",
                "DATA_VERIFIED",
                {
                    "session_id": session_id,
                    "query": payload["query"],
                    "report": str(result),
                },
            )
        except Exception as exc:
            logging.exception("Verification stage failed for session %s", session_id)
            await event_bus.fail_response(session_id, PipelineError(f"Verification stage failed: {exc}"))


async def fact_checker_consumer_node() -> None:
    agents = VeritasAgents()
    fact_checker = agents.fact_checking_agent([rag_fact_check_tool, kg_build_tool, kg_validate_tool])

    async for event in event_bus.subscribe("fact_check_stream"):
        payload = event["payload"]
        session_id = payload["session_id"]
        try:
            task = Task(
                description=(
                    "Read the validated report. Extract key entities and relationships, bind them with the "
                    "Knowledge Graph Entity Builder tool, validate them with the Knowledge Graph Validator, "
                    "and cross-check major claims with the RAG Fact Checker.\n\n"
                    f"REPORT:\n{payload['report']}"
                ),
                expected_output="A verified intelligence report with contradictions and evidence noted explicitly.",
                agent=fact_checker,
            )
            crew = Crew(agents=[fact_checker], tasks=[task], verbose=False)
            result = await _run_crew(crew, settings.AGENT_TASK_TIMEOUT_SECONDS)
            await event_bus.publish(
                "misinformation_stream",
                "FACTS_CHECKED",
                {
                    "session_id": session_id,
                    "query": payload["query"],
                    "report": str(result),
                },
            )
        except Exception as exc:
            logging.exception("Fact checking stage failed for session %s", session_id)
            await event_bus.fail_response(session_id, PipelineError(f"Fact-checking stage failed: {exc}"))


async def misinformation_consumer_node() -> None:
    agents = VeritasAgents()
    fake_news_analyzer = agents.fake_news_agent([fake_news_detector_tool])
    critic = agents.critic_agent([truth_scoring_tool])

    async for event in event_bus.subscribe("misinformation_stream"):
        payload = event["payload"]
        session_id = payload["session_id"]
        query = payload["query"]

        try:
            scan_task = Task(
                description=(
                    "Review the report for clickbait, emotional language, or misinformation indicators using "
                    "the Clickbait and Fake News Detector tool.\n\n"
                    f"REPORT:\n{payload['report']}"
                ),
                expected_output="A report annotated with any fake-news classifier output.",
                agent=fake_news_analyzer,
            )
            critic_task = Task(
                description=(
                    "Review the report for contradictions and run the Truth Scoring Engine on any verifiable "
                    "metrics you can extract. Do not invent sources or scores that are not grounded in the "
                    "evidence provided."
                ),
                expected_output="A concise final report grounded only in validated evidence.",
                agent=critic,
            )

            crew = Crew(
                agents=[fake_news_analyzer, critic],
                tasks=[scan_task, critic_task],
                process=Process.sequential,
                verbose=False,
            )
            result = await _run_crew(crew, settings.AGENT_TASK_TIMEOUT_SECONDS)
            formatted_response = build_query_response(query, str(result))

            consensus_overrider = ConsensusEngine()
            unified_consensus_response = consensus_overrider.evaluate(formatted_response)

            explainer = ExplainabilityLayer()
            explained_response = explainer.evaluate(unified_consensus_response)

            firewall = HallucinationFirewall()
            final_response = firewall.evaluate(explained_response)

            alert_engine = AlertEngine()
            triggered_alerts = alert_engine.evaluate(final_response)
            if triggered_alerts:
                record_alerts(triggered_alerts)
                for alert in triggered_alerts:
                    await event_bus.publish("global_alerts", "ALERT_TRIGGERED", alert)

            await event_bus.resolve_response(session_id, final_response)
        except Exception as exc:
            logging.exception("Final pipeline stage failed for session %s", session_id)
            await event_bus.fail_response(session_id, PipelineError(f"Final validation stage failed: {exc}"))


async def run_multi_agent_pipeline(query: str) -> QueryResponse:
    normalized_query = " ".join(query.strip().split())
    if not normalized_query:
        raise PipelineError("Query string cannot be empty.")

    existing_future = _inflight_queries.get(normalized_query.lower())
    if existing_future is not None:
        return await asyncio.shield(existing_future)

    loop = asyncio.get_running_loop()
    shared_future = loop.create_future()
    _inflight_queries[normalized_query.lower()] = shared_future
    session_id = str(uuid.uuid4())
    response_future = loop.create_future()
    event_bus.response_futures[session_id] = response_future

    try:
        agents = VeritasAgents()
        tools = [news_search_tool, web_scrape_tool, rss_reader_tool]

        planner = agents.planner_agent()
        executor = agents.executor_agent(tools)

        planning_task = Task(
            description=f"Analyze query: '{normalized_query}'. Create a step-by-step strategy to gather evidence.",
            expected_output="A compact, actionable execution plan.",
            agent=planner,
        )

        execution_task = Task(
            description=(
                "Using the planner's strategy, execute the available tools sequentially to collect evidence. "
                "Do not invent URLs, sources, or evidence that are not returned by the tools."
            ),
            expected_output="A compiled evidence report containing raw facts and source links.",
            agent=executor,
        )

        crew = Crew(
            agents=[planner, executor],
            tasks=[planning_task, execution_task],
            process=Process.sequential,
            verbose=False,
        )
        raw_result = await _run_crew(crew, settings.AGENT_TASK_TIMEOUT_SECONDS)

        await event_bus.publish(
            "verification_stream",
            "DATA_COLLECTED",
            {
                "session_id": session_id,
                "query": normalized_query,
                "report": str(raw_result),
            },
        )

        finalized_response = await asyncio.wait_for(
            asyncio.shield(response_future),
            timeout=settings.PIPELINE_TIMEOUT_SECONDS,
        )
        shared_future.set_result(finalized_response)
        return finalized_response
    except asyncio.TimeoutError as exc:
        message = "The verification pipeline exceeded its timeout budget."
        fallback = _fallback_response(normalized_query, message)
        if not shared_future.done():
            shared_future.set_result(fallback)
        return fallback
    except Exception as exc:
        logging.exception("Pipeline failed for query '%s'", normalized_query)
        if not shared_future.done():
            shared_future.set_exception(exc)
        raise
    finally:
        event_bus.response_futures.pop(session_id, None)
        _inflight_queries.pop(normalized_query.lower(), None)


def deploy_event_consumers() -> List[asyncio.Task]:
    global _consumer_tasks
    if _consumer_tasks:
        return _consumer_tasks

    _consumer_tasks = [
        asyncio.create_task(verification_consumer_node(), name="verification_consumer"),
        asyncio.create_task(fact_checker_consumer_node(), name="fact_checker_consumer"),
        asyncio.create_task(misinformation_consumer_node(), name="misinformation_consumer"),
    ]
    logging.info("Event streaming consumers engaged.")
    return _consumer_tasks


async def shutdown_event_consumers() -> None:
    global _consumer_tasks
    for task in _consumer_tasks:
        task.cancel()
    for task in _consumer_tasks:
        with suppress(asyncio.CancelledError):
            await task
    _consumer_tasks = []
    await event_bus.shutdown()
