import logging
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from api.server import router as api_router
from api.websockets import router as ws_router
from config.settings import settings
from contextlib import asynccontextmanager
from models.schemas import ErrorResponse
from pipelines.multi_agent_pipeline import deploy_event_consumers, shutdown_event_consumers

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.consumer_tasks = deploy_event_consumers()
    yield
    await shutdown_event_consumers()

app = FastAPI(
    title=settings.APP_NAME,
    description="Real-time news intelligence and fake news detection API",
    version="0.1.0",
    lifespan=lifespan
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
        content=ErrorResponse(message="Request validation failed.",).model_dump() | {
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

if __name__ == "__main__":
    import uvicorn
    # Make sure to run uvicorn on a specific port since we are async.
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
