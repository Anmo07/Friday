import asyncio
import hashlib
import logging
import uuid
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, List, Optional
from dataclasses import dataclass, field

from crewai import Crew, Task

from agents.veritas_agents import VeritasAgents
from config.settings import settings
from core.alert_engine import AlertEngine, record_alerts
from core.consensus_engine import ConsensusEngine
from core.explainability_layer import ExplainabilityLayer
from core.firewall import HallucinationFirewall
from core.redis_cache import redis_cache
from models.schemas import QueryResponse
from pipelines.event_bus import event_bus
from pipelines.response_builder import build_query_response
from tools.kg_tools import kg_validate_tool
from tools.news_api import news_search_tool
from tools.nlp_tools import fake_news_detector_tool
from tools.rss_reader import rss_reader_tool
from tools.truth_tools import truth_scoring_tool
from tools.verification_tools import domain_credibility_tool, rag_fact_check_tool
from tools.web_scraper import web_scrape_tool


class PipelineError(RuntimeError):
    """Raised when a pipeline session cannot complete safely."""


@dataclass
class PipelineContext:
    session_id: str
    query: str
    raw_report: str = ""
    verification_result: Optional[str] = None
    fact_check_result: Optional[str] = None
    misinformation_result: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    progress_callback: Optional[Callable[[str, str], Awaitable[None]]] = None


_consumer_tasks: List[asyncio.Task] = []
_inflight_queries: Dict[str, asyncio.Future] = {}
_validation_agent_semaphore = asyncio.Semaphore(max(1, settings.MAX_PARALLEL_TOOLS))



async def _run_crew_async(crew: Crew, timeout_seconds: int) -> str:
    """
    Executes a crew kickoff in a non-blocking thread and returns the result.
    """
    try:
        # Phase 10: Ensure safe async execution of CrewAI logic
        result = await asyncio.wait_for(
            asyncio.to_thread(crew.kickoff),
            timeout=timeout_seconds,
        )
        return str(result)
    except asyncio.TimeoutError as exc:
        raise PipelineError("Agent execution timed out.") from exc
    except Exception as exc:
        logging.error(f"Crew execution error: {exc}")
        raise PipelineError(str(exc)) from exc


async def _get_agent_cache(key: str) -> Optional[str]:
    """Phase 3: Hash-based agent output caching."""
    if not redis_cache._redis:
        return None
    try:
        return await redis_cache._redis.get(f"agent_cache:{key}")
    except Exception:
        return None


async def _set_agent_cache(key: str, value: str, ttl: int = 1800):
    """Phase 3: Cache agent outputs with TTL."""
    if not redis_cache._redis:
        return
    try:
        await redis_cache._redis.setex(f"agent_cache:{key}", ttl, value)
    except Exception:
        pass


def _hash_payload(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


async def _emit_progress(
    progress_callback: Optional[Callable[[str, str], Awaitable[None]]],
    stage: str,
    message: str,
) -> None:
    if progress_callback:
        await progress_callback(stage, message)


async def _run_validation_agent(
    *,
    agent_name: str,
    stage: str,
    report: str,
    agent_builder: Callable[[List[Any]], Any],
    tools: List[Any],
    task_description: str,
    expected_output: str,
    progress_callback: Optional[Callable[[str, str], Awaitable[None]]],
    timeout_seconds: int = 40,
) -> str:
    cache_key = _hash_payload(f"{agent_name}:{report}")
    cached_output = await _get_agent_cache(cache_key)
    if cached_output:
        await _emit_progress(
            progress_callback,
            stage,
            f"{agent_name} cache hit.",
        )
        return cached_output

    await _emit_progress(progress_callback, stage, f"{agent_name} started...")
    agent = agent_builder(tools)
    task = Task(
        description=task_description,
        expected_output=expected_output,
        agent=agent,
    )
    crew = Crew(agents=[agent], tasks=[task], verbose=False)

    async with _validation_agent_semaphore:
        output = await _run_crew_async(crew, timeout_seconds)

    await _set_agent_cache(cache_key, output)
    await _emit_progress(progress_callback, stage, f"{agent_name} completed.")
    return output


async def _run_parallel_validation(
    *,
    agents: VeritasAgents,
    query: str,
    raw_report: str,
    progress_callback: Optional[Callable[[str, str], Awaitable[None]]] = None,
) -> Dict[str, str]:
    verification_tools = [domain_credibility_tool, kg_validate_tool]
    fact_check_tools = [rag_fact_check_tool, domain_credibility_tool, kg_validate_tool]
    misinformation_tools = [fake_news_detector_tool, truth_scoring_tool]

    tasks = [
        _run_validation_agent(
            agent_name="Verification Agent",
            stage="verification",
            report=raw_report,
            agent_builder=agents.verification_agent,
            tools=verification_tools,
            task_description=(
                f"Verify source credibility and evidence integrity for query: '{query}'.\n"
                f"Report:\n{raw_report}"
            ),
            expected_output="Source credibility checks with verified/unverified evidence flags.",
            progress_callback=progress_callback,
        ),
        _run_validation_agent(
            agent_name="Fact Checker",
            stage="fact_check",
            report=raw_report,
            agent_builder=agents.fact_checking_agent,
            tools=fact_check_tools,
            task_description=(
                f"Cross-check factual claims for query: '{query}'.\n"
                f"Report:\n{raw_report}"
            ),
            expected_output="Claim-by-claim fact-check results with support/contradiction notes.",
            progress_callback=progress_callback,
        ),
        _run_validation_agent(
            agent_name="Misinformation Analyzer",
            stage="misinformation",
            report=raw_report,
            agent_builder=agents.misinformation_agent,
            tools=misinformation_tools,
            task_description=(
                f"Analyze narrative manipulation and misinformation risk for query: '{query}'.\n"
                f"Report:\n{raw_report}"
            ),
            expected_output="Misinformation risk summary with manipulation indicators and confidence.",
            progress_callback=progress_callback,
        ),
    ]

    verification_result, fact_check_result, misinformation_result = await asyncio.gather(
        *tasks
    )
    return {
        "verification_result": verification_result,
        "fact_check_result": fact_check_result,
        "misinformation_result": misinformation_result,
    }


async def run_multi_agent_pipeline(
    query: str,
    progress_callback: Optional[Callable[[str, str], Awaitable[None]]] = None,
) -> QueryResponse:
    """
    Veritas AI Main Pipeline - Optimized for Low Latency.
    Phases 1-11 implemented here.
    """
    normalized_query = " ".join(query.strip().split())
    if not normalized_query:
        raise PipelineError("Query string cannot be empty.")

    # Deduplicate in-flight queries
    existing_future = _inflight_queries.get(normalized_query.lower())
    if existing_future is not None:
        return await asyncio.shield(existing_future)

    loop = asyncio.get_running_loop()
    shared_future = loop.create_future()
    _inflight_queries[normalized_query.lower()] = shared_future
    
    session_id = str(uuid.uuid4())
    ctx = PipelineContext(session_id=session_id, query=normalized_query, progress_callback=progress_callback)

    try:
        agents = VeritasAgents()

        # Step 1: Research
        await _emit_progress(
            progress_callback,
            "data_collection",
            "Researching and gathering sources...",
        )

        research_key = _hash_payload(f"research:{normalized_query}")
        cached_research = await _get_agent_cache(research_key)

        if cached_research:
            ctx.raw_report = cached_research
        else:
            tools = [news_search_tool, web_scrape_tool, rss_reader_tool]
            researcher = agents.research_agent(tools)
            task = Task(
                description=f"Gather evidence for: '{query}'. Provide raw facts and sources.",
                expected_output="A list of facts and source URLs.",
                agent=researcher
            )
            crew = Crew(agents=[researcher], tasks=[task], verbose=False)
            ctx.raw_report = await _run_crew_async(crew, 45)
            await _set_agent_cache(research_key, ctx.raw_report)

        # Step 2: Parallel validation
        await _emit_progress(
            progress_callback,
            "parallel_agents",
            "Running verification, fact-checking, and misinformation analysis in parallel...",
        )

        validation_results = await _run_parallel_validation(
            agents=agents,
            query=normalized_query,
            raw_report=ctx.raw_report,
            progress_callback=progress_callback,
        )
        ctx.verification_result = validation_results["verification_result"]
        ctx.fact_check_result = validation_results["fact_check_result"]
        ctx.misinformation_result = validation_results["misinformation_result"]

        # --- PHASE 11: RESPONSE BUILDING ---
        await _emit_progress(
            progress_callback,
            "scoring",
            "Finalizing truth assessment score...",
        )

        response = await _build_final_response(ctx)
        
        shared_future.set_result(response)
        return response

    except Exception as exc:
        logging.exception("Pipeline failed")
        fallback = _fallback_response(normalized_query, str(exc))
        if not shared_future.done():
            shared_future.set_result(fallback)
        return fallback

    finally:
        _inflight_queries.pop(normalized_query.lower(), None)


async def _build_final_response(ctx: PipelineContext) -> QueryResponse:
    """
    Constructs the final QueryResponse object using the consensus and engine layers.
    """
    combined_report = "\n\n".join(filter(None, [
        ctx.raw_report,
        ctx.verification_result,
        ctx.fact_check_result,
        ctx.misinformation_result
    ]))

    # Phase 11: Optimized response builder mapping
    formatted_response = build_query_response(ctx.query, combined_report)

    # Core logic modules (fast, synchronous calculation)
    consensus_engine = ConsensusEngine()
    unified_response = consensus_engine.evaluate(formatted_response)

    explainer = ExplainabilityLayer()
    explained_response = explainer.evaluate(unified_response)

    firewall = HallucinationFirewall()
    final_response = firewall.evaluate(explained_response)

    # Alert generation
    alert_engine = AlertEngine()
    triggered_alerts = alert_engine.evaluate(final_response)
    if triggered_alerts:
        record_alerts(triggered_alerts)
        for alert in triggered_alerts:
            await event_bus.publish("global_alerts", "ALERT_TRIGGERED", alert)

    return final_response


async def run_fast_pipeline(query: str) -> QueryResponse:
    """
    Phase 2: Fast Path implementation.
    Single LLM call using a lightweight model.
    """
    agents = VeritasAgents()
    fast_agent = agents.fast_validation_agent()
    
    task = Task(
        description=f"Quick truth assessment for: '{query}'",
        expected_output="Factual summary, sources, and truth score.",
        agent=fast_agent
    )
    crew = Crew(agents=[fast_agent], tasks=[task], verbose=False)
    result = await _run_crew_async(crew, 30)
    
    return build_query_response(query, str(result))


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


def deploy_event_consumers() -> List[asyncio.Task]:
    global _consumer_tasks
    if _consumer_tasks:
        return _consumer_tasks
    logging.info("Optimized parallel pipeline initialized.")
    return _consumer_tasks


async def shutdown_event_consumers() -> None:
    await event_bus.shutdown()
