import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.server import router as api_router
from api.websockets import router as ws_router
from config.settings import settings
from core.redis_cache import init_redis_cache, close_redis_cache
from models.multi_llm import llm_manager
from models.schemas import ErrorResponse
from pipelines.multi_agent_pipeline import (
    deploy_event_consumers,
    shutdown_event_consumers,
)

logger = logging.getLogger(__name__)


async def _preload_models():
    try:
        logger.info("Preloading LLM models...")
        models = await llm_manager.preload_models()
        logger.info(f"Preloaded models: {models}")
    except Exception as e:
        logger.warning(f"Model preloading skipped: {e}")


async def _init_services():
    logger.info("Initializing services...")
    await init_redis_cache()
    await _preload_models()
    deploy_event_consumers()
    logger.info("Services initialized successfully")


async def _cleanup_services():
    logger.info("Cleaning up services...")
    await close_redis_cache()
    await shutdown_event_consumers()
    logger.info("Services cleaned up successfully")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _init_services()
    yield
    await _cleanup_services()


app = FastAPI(
    title=settings.APP_NAME,
    description="Real-time news intelligence and fake news detection API",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials="*" not in settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            message="Request validation failed.",
        ).model_dump()
        | {
            "details": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_, exc: Exception):
    logging.exception("Unhandled application exception", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(message="Internal server error.").model_dump(),
    )


app.include_router(api_router)
app.include_router(ws_router)


@app.get("/api/v1/health")
async def health_check():
    from datetime import datetime

    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": "0.2.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000)
