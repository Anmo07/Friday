import asyncio
import json
import logging
import os
import time
import sys
from contextlib import asynccontextmanager, suppress
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings
from app.core.cache import cache

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def _init_cache():
    try:
        await cache.connect(redis_url=settings.redis_url, timeout=2.0)
    except Exception as e:
        logger.warning(f"Cache init partial failure: {e}")


async def _init_databases():
    try:
        from core.history_store import init_history_database

        await asyncio.to_thread(init_history_database)
    except Exception as e:
        logger.warning(f"History DB init failed: {e}")
    try:
        from feedback.feedback_service import init_feedback_database

        await asyncio.to_thread(init_feedback_database)
    except Exception as e:
        logger.warning(f"Feedback DB init failed: {e}")


async def _preload_models_background():
    try:
        from models.multi_llm import llm_manager

        await llm_manager.preload_models()
    except Exception as e:
        logger.warning(f"Background model preload skipped: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await asyncio.gather(_init_cache(), _init_databases(), return_exceptions=True)
    try:
        from core.pipeline import FridayPipeline

        app.state.pipeline = FridayPipeline()
    except Exception as e:
        logger.error(f"Pipeline init failed: {e}", exc_info=True)
        app.state.pipeline = None
    preload_task = asyncio.create_task(_preload_models_background())
    yield
    preload_task.cancel()
    with suppress(asyncio.CancelledError):
        await preload_task
    if hasattr(app.state, "pipeline") and app.state.pipeline:
        try:
            app.state.pipeline.graph_db.close()
        except:
            pass
    await cache.close()


app = FastAPI(title="Friday", version="2.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TimeoutMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await asyncio.wait_for(
                call_next(request), timeout=settings.PIPELINE_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError:
            return JSONResponse(status_code=504, content={"error": "Request timeout"})
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"error": "Internal server error", "detail": str(e)},
            )


app.add_middleware(TimeoutMiddleware)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"error": "Internal server error"})


@app.get("/")
async def root_redirect():
    return {"status": "ok", "service": "Friday Backend"}


from app.api.routes import router as api_router
from app.api.websocket import ws_router

app.include_router(api_router)
app.include_router(ws_router)
