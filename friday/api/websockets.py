import asyncio
import json
import logging
import time
from contextlib import suppress
from datetime import datetime
from typing import Optional, Callable, Awaitable, Any, Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from config.settings import settings
from core.adaptive_router import classify_depth, detect_voice_command, DepthLevel
from core.smart_cache import smart_cache
from pipelines.event_bus import event_bus
from pipelines.adaptive_pipeline import run_adaptive_pipeline


router = APIRouter(prefix="/ws")


# ── Chat-mode patterns (bypass pipeline entirely) ──
import re
_CHAT_PATTERN = re.compile(
    r"^(hi|hello|hey|good\s+(morning|evening|night)|thanks|thank\s+you|"
    r"bye|goodbye|how\s+are\s+you|what'?s?\s+up|yo|sup|ok|okay|yes|no|"
    r"got\s+it|sure|cool|nice|great|alright|fine)[\s!?.]*$",
    re.IGNORECASE,
)

_CHAT_RESPONSES: Dict[str, str] = {
    "hi": "Hey Boss, what do you need?",
    "hello": "Hello! I'm ready.",
    "hey": "Hey, what's up?",
    "thanks": "Anytime, Boss.",
    "thank you": "You got it.",
    "bye": "Catch you later, Boss.",
    "goodbye": "Later!",
    "how are you": "Running smooth. What do you need?",
    "yo": "Yo. What's the mission?",
    "ok": "Standing by.",
    "yes": "Got it.",
    "no": "Alright.",
    "sure": "On it.",
    "cool": "Cool.",
    "nice": "👍",
    "great": "Let's keep going.",
}


def _get_chat_response(query: str) -> Optional[str]:
    """Instant response for simple chat — zero pipeline cost."""
    normalized = " ".join(query.strip().split()).lower().rstrip("!?.")
    if _CHAT_PATTERN.match(query.strip()):
        # Check exact matches first
        for key, response in _CHAT_RESPONSES.items():
            if normalized.startswith(key):
                return response
        return "I'm listening, Boss."
    return None


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
    await websocket.send_json(payload)


async def _send_progress(
    websocket: WebSocket,
    stage: str,
    progress: int,
    custom_message: Optional[str] = None,
):
    await _send_message(
        websocket, status="processing", message=custom_message or stage, progress=progress
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

            # ── FAST PATH 1: Voice command (instant) ──
            voice_cmd = detect_voice_command(query)
            if voice_cmd:
                await _send_message(
                    websocket,
                    status="voice_command",
                    data={"action": voice_cmd, "query": query},
                    message=f"Voice command: {voice_cmd}",
                )
                continue

            # ── FAST PATH 2: Simple chat (instant, no pipeline) ──
            chat_response = _get_chat_response(query)
            if chat_response:
                await _send_message(
                    websocket,
                    status="complete",
                    data={
                        "query": query,
                        "summary": chat_response,
                        "facts": [],
                        "sources": [],
                        "contradictions": [],
                        "fake_probability": 0.0,
                        "confidence_score": 1.0,
                        "truth_score": 1.0,
                        "status": "verified",
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "depth_level": 0,
                        "latency_ms": round((time.time() - start_time) * 1000, 1),
                    },
                    message=chat_response,
                    depth_level=0,
                )
                continue

            # ── FAST PATH 3: Smart cache (in-memory only, <1ms) ──
            cached_result = await smart_cache.get_query(query)
            if cached_result is not None:
                latency_ms = (time.time() - start_time) * 1000
                await _send_message(
                    websocket,
                    status="complete",
                    data=cached_result.model_dump(),
                    message=f"Cache hit — {latency_ms:.0f}ms",
                    depth_level=1,
                )
                continue

            # ── Route to adaptive depth ──
            depth_decision = classify_depth(query, force_deep=force_deep)

            await _send_message(
                websocket,
                status="processing",
                message=f"L{depth_decision.level}: {depth_decision.reasoning}",
                progress=15,
                depth_level=int(depth_decision.level),
            )

            # ── Progress callback (lightweight) ──
            progress_map = {
                "routing": 20, "data_collection": 30, "parallel_agents": 50,
                "verification": 60, "scoring": 85, "generating": 90,
                "complete": 100,
            }

            async def progress_callback(stage: str, message: str):
                await _send_progress(websocket, stage, progress_map.get(stage, 50), message)

            # ── Stream callback for partial agent results ──
            async def stream_callback(event: str, agent_name: str, data: Dict[str, Any]):
                await _send_message(
                    websocket,
                    status="agent_update",
                    data=data,
                    message=f"{agent_name} done",
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

                latency_ms = (time.time() - start_time) * 1000

                complete_data = response.model_dump()
                complete_data["depth_level"] = int(depth_decision.level)
                complete_data["latency_ms"] = round(latency_ms, 1)

                await _send_message(
                    websocket,
                    status="complete",
                    data=complete_data,
                    message=f"Done in {latency_ms:.0f}ms (L{depth_decision.level})",
                    depth_level=int(depth_decision.level),
                )
            except Exception as exc:
                logging.exception("Pipeline failed")
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
