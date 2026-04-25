"""WebSocket endpoints for real-time streaming."""
import asyncio
import json
import logging
import time
from typing import Optional, Callable, Awaitable

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.cache import cache
from app.core.router import route, RouteDecision
from app.pipeline.fast_pipeline import fast_pipeline
from app.pipeline.deep_pipeline import deep_pipeline
from app.voice.stt import transcribe
from app.voice.tts import speak

logger = logging.getLogger(__name__)

ws_router = APIRouter()


# ---- WebSocket Helpers ----

async def _send_json(ws: WebSocket, data: dict):
    """Send JSON message, silently handle disconnects."""
    try:
        await ws.send_json(data)
    except Exception:
        pass


async def _send_progress(ws: WebSocket, stage: str, progress: int, message: str):
    """Send structured progress update."""
    await _send_json(ws, {
        "status": "processing",
        "stage": stage,
        "progress": min(progress, 99),  # 100 is reserved for complete
        "message": message,
    })


async def _create_progress_callback(ws: WebSocket) -> Callable:
    """Create a progress callback that streams updates to WebSocket."""
    stage_progress = {
        "processing": 10,
        "data_collection": 30,
        "verification": 50,
        "fact_check": 60,
        "scoring": 75,
        "generating": 85,
        "complete": 100,
    }

    async def callback(stage: str, message: str):
        progress = stage_progress.get(stage, 50)
        await _send_progress(ws, stage, progress, message)

    return callback


# ---- Main Query WebSocket ----

@ws_router.websocket("/ws/stream")
async def ws_stream(websocket: WebSocket):
    """
    Main WebSocket endpoint for query streaming.

    Receives: {"query": "...", "deep": false}
    Sends:
      - {"status": "processing", "stage": "...", "progress": 0-99, "message": "..."}
      - {"status": "complete", "data": {...QueryResponse...}, "progress": 100}
      - {"status": "error", "error": {"message": "..."}}
    """
    await websocket.accept()
    logger.info("WebSocket client connected: /ws/stream")

    try:
        while True:
            # Receive query
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await _send_json(websocket, {
                    "status": "error",
                    "error": {"message": "Invalid JSON"},
                })
                continue

            query = msg.get("query", "").strip()
            deep = msg.get("deep", False)

            if not query:
                await _send_json(websocket, {
                    "status": "error",
                    "error": {"message": "Query is required"},
                })
                continue

            start = time.monotonic()

            # Check cache
            await _send_progress(websocket, "cache_check", 5, "Checking cache...")
            cached = await cache.get(query)
            if cached is not None:
                cached["_cached"] = True
                await _send_json(websocket, {
                    "status": "complete",
                    "data": cached,
                    "progress": 100,
                    "message": "Served from cache",
                })
                continue

            # Route and execute
            await _send_progress(websocket, "routing", 10, "Analyzing query...")

            progress_callback = await _create_progress_callback(websocket)

            try:
                if deep or route(query) == RouteDecision.DEEP:
                    response = await deep_pipeline(query, progress_callback=progress_callback)
                else:
                    response = await fast_pipeline(query, progress_callback=progress_callback)

                response["latency_ms"] = round((time.monotonic() - start) * 1000, 1)

                # Cache result
                await cache.set(query, response)

                # Log to history (non-blocking)
                try:
                    from core.history_store import log_query_result
                    from models.schemas import QueryResponse

                    payload = QueryResponse(**response)
                    asyncio.create_task(asyncio.to_thread(log_query_result, payload, "public"))
                except Exception:
                    pass

                # Send complete response
                await _send_json(websocket, {
                    "status": "complete",
                    "data": response,
                    "progress": 100,
                    "message": "Analysis complete",
                })

            except asyncio.TimeoutError:
                await _send_json(websocket, {
                    "status": "error",
                    "error": {"message": "Analysis timed out"},
                })
            except Exception as e:
                logger.error(f"Pipeline error: {e}", exc_info=True)
                await _send_json(websocket, {
                    "status": "error",
                    "error": {"message": f"Analysis failed: {str(e)}"},
                })

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected: /ws/stream")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)


# ---- Voice WebSocket ----

@ws_router.websocket("/ws/voice")
async def ws_voice(websocket: WebSocket):
    """
    Voice WebSocket: receives audio bytes, returns text + audio response.

    Flow: Audio bytes -> STT -> Pipeline -> TTS -> Audio bytes
    """
    await websocket.accept()
    logger.info("WebSocket client connected: /ws/voice")

    try:
        while True:
            # Receive audio bytes
            audio_bytes = await websocket.receive_bytes()

            if not audio_bytes:
                continue

            try:
                # Progress: Listening received
                await _send_json(websocket, {
                    "status": "processing",
                    "stage": "transcribing",
                    "progress": 20,
                    "message": "Transcribing speech...",
                })

                # STT
                text = await transcribe(audio_bytes)

                if not text:
                    await _send_json(websocket, {
                        "status": "error",
                        "error": {"message": "Could not transcribe audio"},
                    })
                    continue

                await _send_json(websocket, {
                    "status": "processing",
                    "stage": "processing",
                    "progress": 40,
                    "message": f"Processing: {text}",
                    "transcription": text,
                })

                # Run fast pipeline
                response = await fast_pipeline(text)

                await _send_json(websocket, {
                    "status": "processing",
                    "stage": "speaking",
                    "progress": 80,
                    "message": "Generating speech...",
                })

                # TTS
                summary = response.get("summary", "Analysis complete")
                speech_bytes = await speak(summary)

                # Send text response
                await _send_json(websocket, {
                    "status": "complete",
                    "data": response,
                    "progress": 100,
                    "message": "Complete",
                    "transcription": text,
                    "has_audio": len(speech_bytes) > 0,
                })

                # Send audio response as bytes
                if speech_bytes:
                    await websocket.send_bytes(speech_bytes)

            except Exception as e:
                logger.error(f"Voice pipeline error: {e}", exc_info=True)
                await _send_json(websocket, {
                    "status": "error",
                    "error": {"message": f"Voice processing failed: {str(e)}"},
                })

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected: /ws/voice")
    except Exception as e:
        logger.error(f"Voice WebSocket error: {e}", exc_info=True)
