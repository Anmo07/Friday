import asyncio
import hashlib
import json
import logging
import uuid
from contextlib import suppress
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field

from crewai import Crew, Process, Task

from agents.veritas_agents import VeritasAgents
from config.settings import settings
from core.alert_engine import AlertEngine, record_alerts
from core.consensus_engine import ConsensusEngine
from core.explainability_layer import ExplainabilityLayer
from core.firewall import HallucinationFirewall
from core.redis_cache import redis_cache, vector_cache
from models.schemas import QueryResponse
from pipelines.event_bus import event_bus
from pipelines.response_builder import build_query_response
from pipelines.retrieval_pipeline import retrieve_relevant_context_async
from tools.kg_tools import kg_build_tool, kg_validate_tool
from tools.news_api import news_search_tool
from tools.nlp_tools import fake_news_detector_tool
from tools.rss_reader import rss_reader_tool
from tools.truth_tools import truth_scoring_tool
from tools.verification_tools import domain_credibility_tool
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
    progress_callback: Optional[Callable[[str, str], None]] = None


_consumer_tasks: List[asyncio.Task] = []
_inflight_queries: Dict[str, asyncio.Future] = {}



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
    if not redis_cache._redis: return None
    try:
        return await redis_cache._redis.get(f"agent_cache:{key}")
    except Exception: return None


async def _set_agent_cache(key: str, value: str, ttl: int = 1800):
    """Phase 3: Cache agent outputs with TTL."""
    if not redis_cache._redis: return
    try:
        await redis_cache._redis.setex(f"agent_cache:{key}", ttl, value)
    except Exception: pass


async def run_multi_agent_pipeline(
    query: str, progress_callback: Optional[Callable[[str, str], None]] = None
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
        
        # --- PHASE 4: REDUCED LLM CALLS (Step 1: Research) ---
        if progress_callback:
            await progress_callback("data_collection", "Researching and gathering sources...")
            
        research_key = hashlib.md5(f"research:{normalized_query}".encode()).hexdigest()
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

        # --- PHASE 8: UNIFIED VALIDATION (Step 2: Analysis) ---
        if progress_callback:
            await progress_callback("analysis", "Validating facts and detecting misinformation...")

        validation_key = hashlib.md5(f"validate:{ctx.raw_report}".encode()).hexdigest()
        cached_validation = await _get_agent_cache(validation_key)

        if cached_validation:
            ctx.verification_result = cached_validation
            ctx.fact_check_result = cached_validation
            ctx.misinformation_result = cached_validation
        else:
            # Phase 6: Optimized RAG call (embedded in validation tools)
            # Phase 8: Unified Validation Agent call
            tools = [domain_credibility_tool, fake_news_detector_tool]
            # Internal Fact Checker uses RAG internally via the tool
            validator = agents.unified_validation_agent(tools)
            
            task = Task(
                description=f"Perform truth assessment on the following report:\n{ctx.raw_report}",
                expected_output="A structured assessment with credibility scores and fact-checks.",
                agent=validator
            )
            crew = Crew(agents=[validator], tasks=[task], verbose=False)
            validation_out = await _run_crew_async(crew, 45)
            
            ctx.verification_result = validation_out
            ctx.fact_check_result = validation_out
            ctx.misinformation_result = validation_out
            await _set_agent_cache(validation_key, validation_out)

        # --- PHASE 11: RESPONSE BUILDING ---
        if progress_callback:
            await progress_callback("scoring", "Finalizing truth assessment score...")

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
    unified_agent = agents.unified_validation_agent() # Will use faster LLM tier
    
    task = Task(
        description=f"Quick truth assessment for: '{query}'",
        expected_output="Factual summary, sources, and truth score.",
        agent=unified_agent
    )
    crew = Crew(agents=[unified_agent], tasks=[task], verbose=False)
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

