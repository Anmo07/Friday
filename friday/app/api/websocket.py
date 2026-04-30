from __future__ import annotations
import asyncio
import json
import logging
import time
from contextlib import suppress
from typing import Awaitable, Callable
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.cache import cache
from app.voice.stt_service import stt_service
from app.voice.tts_service import tts_service
from core.personality import friday_personality

logger = logging.getLogger(__name__)
ws_router = APIRouter()


async def _send_json(ws: WebSocket, data: dict) -> None:
    try:
        await ws.send_json(data)
    except Exception:
        logger.debug("WebSocket send skipped; client likely disconnected")


async def _send_progress(
    ws: WebSocket, stage: str, progress: int, message: str
) -> None:
    await _send_json(
        ws,
        {
            "status": "processing",
            "stage": stage,
            "progress": min(progress, 99),
            "message": message,
        },
    )


async def _create_progress_callback(
    ws: WebSocket,
) -> Callable[[str, str], Awaitable[None]]:
    stage_progress = {
        "action": 20,
        "news_fetch": 30,
        "processing": 35,
        "data_collection": 45,
        "verification": 60,
        "fact_check": 70,
        "scoring": 80,
        "generating": 88,
        "complete": 100,
    }

    async def callback(stage: str, message: str) -> None:
        await _send_progress(ws, stage, stage_progress.get(stage, 50), message)

    return callback


async def _news_streamer(ws: WebSocket, query: str):
    from tools.news_api import news_search_tool

    seen_news = set()
    try:
        while True:
            news_data = await asyncio.to_thread(news_search_tool, query)
            if news_data and news_data not in seen_news:
                seen_news.add(news_data)
                await _send_json(
                    ws,
                    {
                        "status": "update",
                        "type": "news_flash",
                        "data": {"update": news_data},
                        "message": "Boss, I found fresh updates on that topic.",
                    },
                )
            await asyncio.sleep(30)
    except asyncio.CancelledError:
        pass


async def _handle_query(
    websocket: WebSocket, query: str, *, deep: bool, tier: str
) -> None:
    start = time.monotonic()
    if tier != "tier_1_fast":
        await _send_progress(websocket, "cache_check", 5, "Checking memory...")
        cached = await cache.get(query)
        if cached is not None:
            cached["_cached"] = True
            await _send_json(
                websocket,
                {
                    "status": "complete",
                    "data": cached,
                    "progress": 100,
                    "message": "Pulled from memory, Boss.",
                },
            )
            return
    pipeline = websocket.app.state.pipeline
    response = await pipeline.run(query)
    response["latency_ms"] = round((time.monotonic() - start) * 1000, 1)
    if tier != "tier_1_fast":
        await cache.set(query, response)
    await _send_json(
        websocket,
        {
            "status": "complete",
            "data": response,
            "progress": 100,
            "message": response.get("response", "Ready, Boss.")[:100] + "...",
        },
    )


@ws_router.websocket("/ws/stream")
async def ws_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    logger.info("WebSocket client connected: /ws/stream")
    greeting = friday_personality.startup_greeting()
    await _send_json(
        websocket,
        {
            "status": "session",
            "message": greeting.message,
            "greeting": greeting.message,
            "period": greeting.period,
            "mode": "assistant",
        },
    )
    current_task: asyncio.Task | None = None
    try:
        while True:
            raw = await websocket.receive_text()
            payload_type = "query"
            deep = False
            query = raw
            try:
                message = json.loads(raw)
                payload_type = message.get("type", "query")
                query = message.get("query", "")
                deep = bool(message.get("deep", False))
            except json.JSONDecodeError:
                pass
            normalized_query = " ".join(str(query).split())
            if payload_type == "interrupt" or friday_personality.detect_interruption(
                normalized_query
            ):
                if current_task and not current_task.done():
                    current_task.cancel()
                    with suppress(asyncio.CancelledError):
                        await current_task
                await _send_json(
                    websocket,
                    {
                        "status": "interrupted",
                        "message": friday_personality.stopping_response(),
                    },
                )
                current_task = None
                continue
            if not normalized_query:
                await _send_json(
                    websocket,
                    {
                        "status": "error",
                        "error": {"message": "Query is required"},
                    },
                )
                continue
            pipeline = websocket.app.state.pipeline
            tier = pipeline.classify(normalized_query)
            if current_task and not current_task.done():
                current_task.cancel()
                with suppress(asyncio.CancelledError):
                    await current_task
                await _send_json(
                    websocket,
                    {
                        "status": "interrupted",
                        "message": friday_personality.stopping_response(),
                    },
                )
            await _send_json(
                websocket,
                {
                    "status": "assistant",
                    "message": "Processing your request, Boss...",
                    "mode": "assistant",
                    "intent": tier,
                },
            )
            current_task = asyncio.create_task(
                _handle_query(
                    websocket,
                    normalized_query,
                    deep=deep,
                    tier=tier,
                )
            )
            if tier == "tier_2_standard":
                asyncio.create_task(_news_streamer(websocket, normalized_query))
    except WebSocketDisconnect:
        logger.info("WebSocket client connected: /ws/stream")
    except Exception as exc:
        logger.error("WebSocket error: %s", exc, exc_info=True)
    finally:
        if current_task and not current_task.done():
            current_task.cancel()
            with suppress(asyncio.CancelledError):
                await current_task


@ws_router.websocket("/ws/voice")
async def ws_voice(websocket: WebSocket) -> None:
    await websocket.accept()
    logger.info("WebSocket client connected: /ws/voice")
    buffered_chunks: list[bytes] = []
    try:
        while True:
            message = await websocket.receive()
            audio_bytes = message.get("bytes")
            text_payload = message.get("text")
            if text_payload:
                try:
                    control = json.loads(text_payload)
                except json.JSONDecodeError:
                    control = {}
                event_type = control.get("type")
                if event_type == "voice_start":
                    buffered_chunks.clear()
                    await _send_progress(
                        websocket, "transcribing", 10, "Voice stream started..."
                    )
                    continue
                if event_type == "voice_chunk":
                    chunk_text = control.get("audio")
                    if isinstance(chunk_text, str):
                        buffered_chunks.append(
                            chunk_text.encode("latin1", errors="ignore")
                        )
                        if len(buffered_chunks) % 5 == 0:
                            partial = await stt_service.transcribe_stream(
                                buffered_chunks
                            )
                            if partial:
                                await _send_json(
                                    websocket,
                                    {"status": "partial_transcript", "text": partial},
                                )
                    continue
                if event_type == "voice_end":
                    audio_bytes = b"".join(buffered_chunks)
                    buffered_chunks.clear()
                elif event_type == "ping":
                    await _send_json(websocket, {"status": "pong"})
                    continue
            if not audio_bytes:
                continue
            await _send_progress(websocket, "transcribing", 20, "Listening...")
            text = await stt_service.transcribe(audio_bytes)
            if not text:
                await _send_json(
                    websocket,
                    {
                        "status": "error",
                        "error": {"message": "Could not transcribe audio"},
                    },
                )
                continue
            pipeline = websocket.app.state.pipeline
            tier = pipeline.classify(text)
            await _send_json(
                websocket,
                {
                    "status": "assistant",
                    "message": "Acknowledged.",
                    "mode": "voice",
                    "intent": tier,
                    "transcription": text,
                },
            )
            response = await pipeline.run(text, voice_mode=True)
            summary = response.get("response", "Ready, Boss.")
            await _send_json(
                websocket,
                {"status": "response_ready", "text": summary},
            )
            await _send_progress(websocket, "speaking", 85, "Talking back...")
            async for chunk in tts_service.stream_audio(summary):
                await websocket.send_bytes(chunk)
            await _send_json(
                websocket,
                {
                    "status": "complete",
                    "data": response,
                    "progress": 100,
                    "message": summary,
                    "transcription": text,
                },
            )
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected: /ws/voice")
    except Exception as exc:
        logger.error("Voice websocket error: %s", exc, exc_info=True)
