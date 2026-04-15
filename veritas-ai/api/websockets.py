import asyncio
import json
import logging
from contextlib import suppress
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from config.settings import settings
from core.cache_layer import query_cache
from core.history_store import log_query_result
from core.security import validate_api_key
from pipelines.event_bus import event_bus
from pipelines.multi_agent_pipeline import run_multi_agent_pipeline


router = APIRouter(prefix="/ws")


async def _send_message(
    websocket: WebSocket,
    *,
    status: str,
    data=None,
    message: Optional[str] = None,
    error: Optional[str] = None,
):
    payload = {"status": status}
    if data is not None:
        payload["data"] = data
    if message is not None:
        payload["message"] = message
    if error is not None:
        payload["error"] = {"message": error}
    await websocket.send_json(payload)


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
            try:
                payload = json.loads(raw_data)
                query = " ".join(str(payload.get("query", "")).split())
            except json.JSONDecodeError:
                query = " ".join(raw_data.split())

            if not query:
                await _send_message(websocket, status="error", error="Query string cannot be empty.")
                continue

            cached_result = query_cache.get(query)
            if cached_result is not None:
                cached_payload = cached_result.model_copy(update={"timestamp": datetime.utcnow().isoformat() + "Z"})
                await asyncio.to_thread(log_query_result, cached_payload)
                await _send_message(websocket, status="processing", message="Cache hit.")
                await _send_message(websocket, status="complete", data=cached_payload.model_dump())
                continue

            await _send_message(websocket, status="processing", message=f"Verifying: {query}")
            try:
                response = await run_multi_agent_pipeline(query)
                query_cache.set(query, response)
                await asyncio.to_thread(log_query_result, response)
                await _send_message(websocket, status="complete", data=response.model_dump())
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
