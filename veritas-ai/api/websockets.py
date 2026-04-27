import asyncio
import json
import logging
import time
from contextlib import suppress
from datetime import datetime
from typing import Optional, Callable, Awaitable, Any, Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from config.settings import settings
from core.cache_layer import query_cache
from core.history_store import log_query_result
from core.redis_cache import redis_cache
from core.adaptive_router import classify_depth, detect_voice_command, DepthLevel
from core.smart_cache import smart_cache
from pipelines.event_bus import event_bus
from pipelines.adaptive_pipeline import run_adaptive_pipeline


router = APIRouter(prefix="/ws")


PROGRESS_STAGES = {
    "cache_check": "Checking cache...",
    "routing": "Analyzing query...",
    "data_collection": "Collecting data from sources...",
    "parallel_agents": "Running parallel analysis...",
    "verification": "Verifying sources...",
    "fact_check": "Cross-referencing facts...",
    "misinformation": "Detecting misinformation...",
    "scoring": "Computing truth score...",
    "generating": "Generating response...",
    "finalizing": "Finalizing response...",
    "complete": "Analysis complete",
}


async def _send_message(
    websocket: WebSocket,
    *,
    status: str,
    data=None,
    message: Optional[str] = None,
    error: Optional[str] = None,
    progress: Optional[int] = None,
    agent: Optional[str] = None,
    depth_level: Optional[int] = None,
    agent_outputs: Optional[Dict[str, Any]] = None,
):
    payload: Dict[str, Any] = {"status": status}
    if data is not None:
        payload["data"] = data
    if message is not None:
        payload["message"] = message
    if error is not None:
        payload["error"] = {"message": error}
    if progress is not None:
        payload["progress"] = progress
    if agent is not None:
        payload["agent"] = agent
    if depth_level is not None:
        payload["depth_level"] = depth_level
    if agent_outputs is not None:
        payload["agent_outputs"] = agent_outputs
    await websocket.send_json(payload)


async def _send_progress(
    websocket: WebSocket,
    stage: str,
    progress: int,
    custom_message: Optional[str] = None,
):
    message = custom_message or PROGRESS_STAGES.get(stage, stage)
    await _send_message(
        websocket, status="processing", message=message, progress=progress
    )


async def stream_alerts_to_client(websocket: WebSocket):
    async for event in event_bus.subscribe("global_alerts"):
        try:
            await _send_message(websocket, status="alert", data=event["payload"])
        except Exception:
            break


def _authorize_websocket(websocket: WebSocket) -> None:
    session_auth = websocket.query_params.get("session_auth")
    if session_auth:
        from core.security import validate_api_key
        validate_api_key(session_auth)
        return
    if not settings.ALLOW_ANONYMOUS_WS:
        raise PermissionError("WebSocket authentication is required.")


@router.websocket("/stream")
async def websocket_query_endpoint(websocket: WebSocket):
    try:
        _authorize_websocket(websocket)
    except Exception as exc:
        await websocket.close(code=4401, reason=str(exc))
        return

    await websocket.accept()
    logging.info("WebSocket connection established.")

    alert_task = asyncio.create_task(stream_alerts_to_client(websocket))
    session_id = None

    try:
        while True:
            raw_data = await websocket.receive_text()
            start_time = time.time()

            try:
                payload = json.loads(raw_data)
                query = " ".join(str(payload.get("query", "")).split())
                force_deep = payload.get("deep", False)
            except json.JSONDecodeError:
                query = " ".join(raw_data.split())
                force_deep = False

            if not query:
                await _send_message(
                    websocket, status="error", error="Query string cannot be empty."
                )
                continue

            # ── Voice command detection ──
            voice_cmd = detect_voice_command(query)
            if voice_cmd:
                await _send_message(
                    websocket,
                    status="voice_command",
                    data={"action": voice_cmd, "query": query},
                    message=f"Voice command: {voice_cmd}",
                )
                continue

            # ── Phase 8: Smart cache check ──
            await _send_progress(websocket, "cache_check", 5, "Checking cache...")

            cached_result = await smart_cache.get_query(query)
            if cached_result is not None:
                latency_ms = (time.time() - start_time) * 1000
                await _send_message(
                    websocket,
                    status="processing",
                    message=f"Cache hit! Response in {latency_ms:.0f}ms",
                    progress=100,
                )
                await _send_message(
                    websocket,
                    status="complete",
                    data=cached_result.model_dump(),
                    depth_level=1,
                )
                continue

            # Also check Redis and local cache
            redis_cached = await redis_cache.get(query)
            if redis_cached is not None:
                latency_ms = (time.time() - start_time) * 1000
                await _send_message(
                    websocket,
                    status="processing",
                    message=f"Cache hit! Response in {latency_ms:.0f}ms",
                    progress=100,
                )
                await _send_message(
                    websocket, status="complete", data=redis_cached.model_dump()
                )
                continue

            local_cached = query_cache.get(query)
            if local_cached is not None:
                latency_ms = (time.time() - start_time) * 1000
                await _send_message(
                    websocket,
                    status="processing",
                    message=f"Cache hit! Response in {latency_ms:.0f}ms",
                    progress=100,
                )
                await _send_message(
                    websocket, status="complete", data=local_cached.model_dump()
                )
                continue

            # ── Phase 1: Route to adaptive depth ──
            depth_decision = classify_depth(query, force_deep=force_deep)

            await _send_message(
                websocket,
                status="processing",
                message=f"Depth L{depth_decision.level}: {depth_decision.reasoning}",
                progress=15,
                depth_level=int(depth_decision.level),
            )

            # ── Progress callback ──
            progress_map = {
                "cache_check": 10,
                "routing": 20,
                "data_collection": 30,
                "parallel_agents": 50,
                "verification": 60,
                "fact_check": 70,
                "misinformation": 80,
                "scoring": 85,
                "generating": 90,
                "finalizing": 95,
                "complete": 100,
            }

            async def progress_callback(stage: str, message: str):
                pct = progress_map.get(stage, 50)
                await _send_progress(websocket, stage, pct, message)

            # ── Phase 3: Stream partial agent results ──
            async def stream_callback(event: str, agent_name: str, data: Dict[str, Any]):
                """Stream partial results to client as agents complete."""
                await _send_message(
                    websocket,
                    status="agent_update",
                    data=data,
                    message=f"{agent_name} completed",
                    agent=agent_name,
                    depth_level=int(depth_decision.level),
                )

            # ── Run adaptive pipeline ──
            try:
                response = await run_adaptive_pipeline(
                    query=query,
                    force_deep=force_deep,
                    session_id=session_id,
                    stream_callback=stream_callback,
                    progress_callback=progress_callback,
                )

                # Store in all cache layers
                await redis_cache.set(query, response)
                query_cache.set(query, response)
                await asyncio.to_thread(log_query_result, response)

                latency_ms = (time.time() - start_time) * 1000

                # Send final complete message with enriched data
                complete_data = response.model_dump()
                complete_data["depth_level"] = int(depth_decision.level)
                complete_data["latency_ms"] = round(latency_ms, 1)
                complete_data["cache_stats"] = smart_cache.get_stats()

                await _send_message(
                    websocket,
                    status="complete",
                    data=complete_data,
                    message=f"Analysis complete in {latency_ms:.0f}ms (L{depth_decision.level})",
                    depth_level=int(depth_decision.level),
                )
            except Exception as exc:
                logging.exception("Adaptive pipeline failed")
                await _send_message(websocket, status="error", error=str(exc))

    except WebSocketDisconnect:
        logging.info("WebSocket client disconnected.")
    except Exception as exc:
        logging.exception("WebSocket execution failed")
        with suppress(Exception):
            await _send_message(websocket, status="error", error=str(exc))
    finally:
        alert_task.cancel()
        with suppress(asyncio.CancelledError):
            await alert_task
