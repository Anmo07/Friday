import asyncio
import logging
import uuid
from contextlib import suppress
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum

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


class QueryComplexity(Enum):
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


@dataclass
class PipelineContext:
    session_id: str
    query: str
    raw_report: str = ""
    verification_result: Optional[str] = None
    fact_check_result: Optional[str] = None
    misinformation_result: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    progress_callback: Optional[Callable[[str, str], None]] = None


_consumer_tasks: List[asyncio.Task] = []
_inflight_queries: Dict[str, asyncio.Future] = {}
_llm_cache: Dict[str, Any] = {}


def _get_cached_llm():
    if "llm" not in _llm_cache:
        _llm_cache["llm"] = VeritasAgents().llm
    return _llm_cache["llm"]


async def _run_crew(crew: Crew, timeout_seconds: int) -> str:
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(crew.kickoff),
            timeout=timeout_seconds,
        )
    except asyncio.TimeoutError as exc:
        raise PipelineError(
            "The agent pipeline timed out before it could complete."
        ) from exc
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


async def _run_parallel_agents(
    ctx: PipelineContext, llm: Any, timeout: int
) -> tuple[str, str, str]:
    agents = VeritasAgents()
    tools = [news_search_tool, web_scrape_tool, rss_reader_tool]

    planner = agents.planner_agent()
    executor = agents.executor_agent(tools)

    planning_task = Task(
        description=f"Analyze query: '{ctx.query}'. Create a step-by-step strategy to gather evidence.",
        expected_output="A compact, actionable execution plan.",
        agent=planner,
    )

    execution_task = Task(
        description=(
            "Using the planner's strategy, execute the available tools to collect evidence. "
            "Do not invent URLs, sources, or evidence that are not returned by the tools."
        ),
        expected_output="A compiled evidence report containing raw facts and source links.",
        agent=executor,
    )

    data_crew = Crew(
        agents=[planner, executor],
        tasks=[planning_task, execution_task],
        process=Process.sequential,
        verbose=False,
    )
    raw_result = await _run_crew(data_crew, timeout)
    ctx.raw_report = str(raw_result)

    verifier = agents.verification_agent([domain_credibility_tool])
    fact_checker = agents.fact_checking_agent(
        [rag_fact_check_tool, kg_build_tool, kg_validate_tool]
    )
    fake_news_analyzer = agents.fake_news_agent([fake_news_detector_tool])

    async def run_verification() -> str:
        task = Task(
            description=(
                "Extract all URLs from the report and evaluate their credibility. "
                f"RAW REPORT:\n{ctx.raw_report}"
            ),
            expected_output="Report with source credibility annotations.",
            agent=verifier,
        )
        crew = Crew(agents=[verifier], tasks=[task], verbose=False)
        return str(await _run_crew(crew, timeout))

    async def run_fact_check() -> str:
        task = Task(
            description=(
                "Extract key entities, validate with Knowledge Graph, and cross-check claims with RAG. "
                f"REPORT:\n{ctx.raw_report}"
            ),
            expected_output="Report with fact validation notes.",
            agent=fact_checker,
        )
        crew = Crew(agents=[fact_checker], tasks=[task], verbose=False)
        return str(await _run_crew(crew, timeout))

    async def run_misinformation_check() -> str:
        task = Task(
            description=(
                "Analyze the report for fake news indicators, emotional manipulation, and misinformation patterns. "
                f"REPORT:\n{ctx.raw_report}"
            ),
            expected_output="Report with misinformation analysis.",
            agent=fake_news_analyzer,
        )
        crew = Crew(agents=[fake_news_analyzer], tasks=[task], verbose=False)
        return str(await _run_crew(crew, timeout))

    try:
        (
            verification_result,
            fact_check_result,
            misinformation_result,
        ) = await asyncio.gather(
            run_verification(),
            run_fact_check(),
            run_misinformation_check(),
            return_exceptions=True,
        )

        ctx.verification_result = (
            verification_result
            if not isinstance(verification_result, Exception)
            else None
        )
        ctx.fact_check_result = (
            fact_check_result if not isinstance(fact_check_result, Exception) else None
        )
        ctx.misinformation_result = (
            misinformation_result
            if not isinstance(misinformation_result, Exception)
            else None
        )

        if isinstance(verification_result, Exception):
            ctx.errors.append(f"Verification failed: {verification_result}")
        if isinstance(fact_check_result, Exception):
            ctx.errors.append(f"Fact check failed: {fact_check_result}")
        if isinstance(misinformation_result, Exception):
            ctx.errors.append(f"Misinformation check failed: {misinformation_result}")

        return (
            ctx.verification_result or ctx.raw_report,
            ctx.fact_check_result or ctx.raw_report,
            ctx.misinformation_result or ctx.raw_report,
        )

    except Exception as exc:
        logging.exception("Parallel agent execution failed")
        ctx.errors.append(str(exc))
        return ctx.raw_report, ctx.raw_report, ctx.raw_report


async def _build_final_response(ctx: PipelineContext) -> QueryResponse:
    combined_report = "\n\n".join(
        filter(
            None,
            [
                ctx.raw_report,
                ctx.verification_result,
                ctx.fact_check_result,
                ctx.misinformation_result,
            ],
        )
    )

    formatted_response = build_query_response(ctx.query, combined_report)

    consensus_engine = ConsensusEngine()
    unified_response = consensus_engine.evaluate(formatted_response)

    explainer = ExplainabilityLayer()
    explained_response = explainer.evaluate(unified_response)

    firewall = HallucinationFirewall()
    final_response = firewall.evaluate(explained_response)

    alert_engine = AlertEngine()
    triggered_alerts = alert_engine.evaluate(final_response)
    if triggered_alerts:
        record_alerts(triggered_alerts)
        for alert in triggered_alerts:
            await event_bus.publish("global_alerts", "ALERT_TRIGGERED", alert)

    return final_response


async def run_multi_agent_pipeline(
    query: str, progress_callback: Optional[Callable[[str, str], None]] = None
) -> QueryResponse:
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

    ctx = PipelineContext(
        session_id=session_id,
        query=normalized_query,
        progress_callback=progress_callback,
    )

    try:
        llm = _get_cached_llm()

        if progress_callback:
            await progress_callback(
                "data_collection", "Collecting data from multiple sources..."
            )

        verification, fact_check, misinformation = await _run_parallel_agents(
            ctx, llm, settings.AGENT_TASK_TIMEOUT_SECONDS
        )

        if progress_callback:
            await progress_callback("validation", "Validating and scoring results...")

        final_response = await _build_final_response(ctx)

        if ctx.errors and progress_callback:
            await progress_callback(
                "warnings", f"Completed with {len(ctx.errors)} issues"
            )

        shared_future.set_result(final_response)
        return final_response

    except asyncio.TimeoutError:
        message = "The verification pipeline exceeded its timeout budget."
        fallback = _fallback_response(normalized_query, message)
        if not shared_future.done():
            shared_future.set_result(fallback)
        return fallback

    except Exception as exc:
        logging.exception("Pipeline failed for query '%s'", normalized_query)
        fallback = _fallback_response(normalized_query, str(exc))
        if not shared_future.done():
            shared_future.set_result(fallback)
        return fallback

    finally:
        _inflight_queries.pop(normalized_query.lower(), None)


async def run_fast_pipeline(query: str) -> QueryResponse:
    normalized_query = " ".join(query.strip().split())
    if not normalized_query:
        raise PipelineError("Query string cannot be empty.")

    existing_future = _inflight_queries.get(normalized_query.lower())
    if existing_future is not None:
        return await asyncio.shield(existing_future)

    loop = asyncio.get_running_loop()
    shared_future = loop.create_future()
    _inflight_queries[normalized_query.lower()] = shared_future

    try:
        agents = VeritasAgents()
        llm = _get_cached_llm()

        unified_agent = agents.unified_validation_agent(llm)

        task = Task(
            description=(
                f"Analyze the following query and provide a quick truth assessment:\n\n"
                f"QUERY: {normalized_query}\n\n"
                "Return a structured report with:\n"
                "1. Key facts identified\n"
                "2. Source credibility assessment\n"
                "3. Potential misinformation indicators\n"
                "4. Truth score (0.0-1.0)"
            ),
            expected_output="A concise truth assessment report.",
            agent=unified_agent,
        )

        crew = Crew(agents=[unified_agent], tasks=[task], verbose=False)
        result = await _run_crew(crew, 60)

        final_response = build_query_response(normalized_query, str(result))

        shared_future.set_result(final_response)
        return final_response

    except Exception as exc:
        logging.exception("Fast pipeline failed for query '%s'", normalized_query)
        fallback = _fallback_response(normalized_query, str(exc))
        if not shared_future.done():
            shared_future.set_result(fallback)
        return fallback

    finally:
        _inflight_queries.pop(normalized_query.lower(), None)


def deploy_event_consumers() -> List[asyncio.Task]:
    global _consumer_tasks
    if _consumer_tasks:
        return _consumer_tasks
    logging.info("Optimized parallel pipeline initialized (no consumer nodes needed).")
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
