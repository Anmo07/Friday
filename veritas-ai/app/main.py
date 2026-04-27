"""Veritas AI — Application entry point.

Fast startup target: < 3 seconds.
- Redis: 2s timeout, graceful fallback to local-only cache
- Model preload: background task (non-blocking)
- SQLite: explicit init, not on import
- Heavy modules: lazy-loaded on first use
"""
import asyncio
import json
import logging
import os
import time
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.cache import cache

logger = logging.getLogger(__name__)


def _debug_log(hypothesis_id: str, message: str, data: dict) -> None:
    # #region agent log
    try:
        with open("/Users/anmol/Downloads/Developer/Friday/.cursor/debug-cf7383.log", "a", encoding="utf-8") as fp:
            fp.write(
                json.dumps(
                    {
                        "sessionId": "cf7383",
                        "runId": "run1",
                        "hypothesisId": hypothesis_id,
                        "location": "app/main.py",
                        "message": message,
                        "data": data,
                        "timestamp": int(time.time() * 1000),
                    }
                )
                + "\n"
            )
    except Exception:
        pass
    # #endregion

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# #region agent log
_debug_log(
    "H3",
    "backend_import_bootstrap",
    {"python_version": sys.version.split(" ")[0], "cwd": os.getcwd()},
)
# #endregion


# ---- Startup / Shutdown ----

async def _init_cache():
    """Initialize cache with Redis (2s timeout, fallback to local)."""
    try:
        await cache.connect(redis_url=settings.redis_url, timeout=2.0)
    except Exception as e:
        logger.warning(f"Cache init partial failure: {e}")


async def _init_databases():
    """Initialize SQLite databases explicitly."""
    try:
        # Import and init history store
        from core.history_store import init_history_database
        await asyncio.to_thread(init_history_database)
        logger.info("History database initialized")
    except Exception as e:
        logger.warning(f"History DB init failed: {e}")

    try:
        # Import and init feedback store
        from feedback.feedback_service import init_feedback_database
        await asyncio.to_thread(init_feedback_database)
        logger.info("Feedback database initialized")
    except Exception as e:
        logger.warning(f"Feedback DB init failed: {e}")


async def _preload_models_background():
    """Preload LLM models in background (non-blocking)."""
    try:
        from models.multi_llm import llm_manager
        models = await llm_manager.preload_models()
        logger.info(f"Background model preload complete: {models}")
    except Exception as e:
        logger.warning(f"Background model preload skipped: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: fast startup, clean shutdown."""
    start_time = time.monotonic()
    logger.info("Starting Veritas AI...")

    # Phase 1: Fast parallel init (cache + databases)
    await asyncio.gather(
        _init_cache(),
        _init_databases(),
        return_exceptions=True,
    )

    elapsed = time.monotonic() - start_time
    logger.info(f"Core services ready in {elapsed:.2f}s")

    # Phase 2: Background model preload (non-blocking)
    preload_task = asyncio.create_task(_preload_models_background())

    logger.info(f"Veritas AI started in {elapsed:.2f}s (models loading in background)")

    yield  # App is running

    # Shutdown
    logger.info("Shutting down Veritas AI...")
    preload_task.cancel()
    try:
        await preload_task
    except asyncio.CancelledError:
        pass
    await cache.close()
    logger.info("Shutdown complete")


# ---- App Creation ----

app = FastAPI(
    title="Veritas AI",
    description="AI-powered news verification and truth scoring",
    version="2.0.0",
    lifespan=lifespan,
)


# ---- Middleware ----

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Timeout + Error handling middleware
class TimeoutMiddleware(BaseHTTPMiddleware):
    """Global request timeout and error handling."""

    async def dispatch(self, request: Request, call_next):
        try:
            response = await asyncio.wait_for(
                call_next(request),
                timeout=settings.PIPELINE_TIMEOUT_SECONDS,
            )
            return response
        except asyncio.TimeoutError:
            logger.error(f"Request timeout: {request.method} {request.url.path}")
            return JSONResponse(
                status_code=504,
                content={"error": "Request timeout", "detail": "The request took too long to process"},
            )
        except Exception as e:
            logger.error(f"Unhandled error: {request.method} {request.url.path} - {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={"error": "Internal server error", "detail": str(e)},
            )


app.add_middleware(TimeoutMiddleware)


# ---- Exception Handlers ----

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler — system never crashes."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred. The system is still operational.",
        },
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Not found", "detail": f"Path {request.url.path} not found"},
    )


# ---- Rate Limiting ----
# Note: slowapi rate limiting is added per-endpoint in routes.py
# We set up the limiter here for shared use

try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded

    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded", "detail": str(exc.detail)},
        )
except ImportError:
    logger.warning("slowapi not installed, rate limiting disabled")
    limiter = None


# ---- Root Route ----

@app.get("/")
async def root_redirect():
    """Root endpoint to prevent 404 on base URL."""
    return {"status": "ok", "service": "Veritas AI Backend", "docs_url": "/docs"}


# ---- Mount Routers ----
# Import routes AFTER app creation to avoid circular imports

from app.api.routes import router as api_router
from app.api.websocket import ws_router

app.include_router(api_router)
app.include_router(ws_router)
