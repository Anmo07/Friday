import asyncio
import json
import logging
import time
from contextlib import suppress
from datetime import datetime
from typing import Optional, Callable, Awaitable

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from config.settings import settings
from core.cache_layer import query_cache
from core.history_store import log_query_result
from core.redis_cache import redis_cache
from core.router import router as query_router
from core.security import validate_api_key
from pipelines.event_bus import event_bus
from pipelines.multi_agent_pipeline import run_multi_agent_pipeline, run_fast_pipeline


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
):
    payload = {"status": status}
    if data is not None:
        payload["data"] = data
    if message is not None:
        payload["message"] = message
    if error is not None:
        payload["error"] = {"message": error}
    if progress is not None:
        payload["progress"] = progress
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
        validate_api_key(session_auth)
        return
    if not settings.ALLOW_ANONYMOUS_WS:
        raise PermissionError("WebSocket authentication is required.")


async def _create_progress_callback(
    websocket: WebSocket,
) -> Callable[[str, str], Awaitable[None]]:
    progress_map = {
        "cache_check": 10,
        "routing": 20,
        "data_collection": 35,
        "parallel_agents": 50,
        "verification": 60,
        "fact_check": 70,
        "misinformation": 80,
        "scoring": 90,
        "finalizing": 95,
        "complete": 100,
        "warnings": 100,
    }

    async def progress_callback(stage: str, message: str):
        progress = progress_map.get(stage, 50)
        await _send_progress(websocket, stage, progress, message)

    return progress_callback


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
    try:
        while True:
            raw_data = await websocket.receive_text()
            start_time = time.time()

            try:
                payload = json.loads(raw_data)
                query = " ".join(str(payload.get("query", "")).split())
            except json.JSONDecodeError:
                query = " ".join(raw_data.split())

            if not query:
                await _send_message(
                    websocket, status="error", error="Query string cannot be empty."
                )
                continue

            await _send_progress(websocket, "cache_check", 5, "Checking cache...")

            cached_result = await redis_cache.get(query)
            if cached_result is not None:
                cached_payload = cached_result.model_copy(
                    update={"timestamp": datetime.utcnow().isoformat() + "Z"}
                )
                await asyncio.to_thread(log_query_result, cached_payload)
                latency_ms = (time.time() - start_time) * 1000
                await _send_message(
                    websocket,
                    status="processing",
                    message=f"Cache hit! Response in {latency_ms:.0f}ms",
                    progress=100,
                )
                await _send_message(
                    websocket, status="complete", data=cached_payload.model_dump()
                )
                continue

            local_cached = query_cache.get(query)
            if local_cached is not None:
                cached_payload = local_cached.model_copy(
                    update={"timestamp": datetime.utcnow().isoformat() + "Z"}
                )
                await asyncio.to_thread(log_query_result, cached_payload)
                latency_ms = (time.time() - start_time) * 1000
                await _send_message(
                    websocket,
                    status="processing",
                    message=f"Cache hit! Response in {latency_ms:.0f}ms",
                    progress=100,
                )
                await _send_message(
                    websocket, status="complete", data=cached_payload.model_dump()
                )
                continue

            await _send_progress(websocket, "routing", 15, "Routing query...")

            routing_result = query_router.route(query)

            if routing_result.decision.value == "fast_path":
                await _send_progress(
                    websocket, "parallel_agents", 30, "Running fast analysis..."
                )
                try:
                    response = await run_fast_pipeline(query)
                    await redis_cache.set(query, response)
                    await asyncio.to_thread(log_query_result, response)
                    await _send_message(
                        websocket, status="complete", data=response.model_dump()
                    )
                except Exception as exc:
                    logging.exception("Fast pipeline failed")
                    await _send_message(websocket, status="error", error=str(exc))
                continue

            await _send_progress(
                websocket, "data_collection", 25, "Starting parallel analysis..."
            )

            progress_callback = await _create_progress_callback(websocket)

            try:
                response = await run_multi_agent_pipeline(
                    query, progress_callback=progress_callback
                )
                await redis_cache.set(query, response)
                query_cache.set(query, response)
                await asyncio.to_thread(log_query_result, response)

                latency_ms = (time.time() - start_time) * 1000
                await _send_message(
                    websocket,
                    status="complete",
                    data=response.model_dump(),
                    message=f"Analysis complete in {latency_ms:.0f}ms",
                )
            except Exception as exc:
                logging.exception("WebSocket pipeline execution failed")
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
