from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.server import router as api_router
from api.websockets import router as ws_router
from config.settings import settings
from contextlib import asynccontextmanager
from pipelines.multi_agent_pipeline import deploy_event_consumers

@asynccontextmanager
async def lifespan(app: FastAPI):
    deploy_event_consumers()
    yield

app = FastAPI(
    title=settings.APP_NAME,
    description="Real-time news intelligence and fake news detection API",
    version="0.1.0",
    lifespan=lifespan
)

# Standard CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(ws_router)

if __name__ == "__main__":
    import uvicorn
    # Make sure to run uvicorn on a specific port since we are async.
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
