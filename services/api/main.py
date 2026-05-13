"""
Jobseeker Orchestrator — FastAPI Backend
Central API that connects Streamlit frontend to vLLM, Qdrant, and Celery.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from config.settings import settings
from services.qdrant.init_collections import init_collections


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialize Qdrant collections. Shutdown: cleanup."""
    logger.info("=== Jobseeker Orchestrator Starting ===")
    logger.info(f"vLLM endpoint: {settings.vllm_base_url}")
    logger.info(f"Qdrant endpoint: {settings.qdrant_url}")
    try:
        init_collections()
        logger.info("Qdrant collections initialized")
    except Exception as e:
        logger.warning(f"Qdrant init deferred (will retry): {e}")
    yield
    logger.info("=== Jobseeker Orchestrator Shutting Down ===")


app = FastAPI(
    title="Jobseeker Orchestrator",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "orchestrator"}


# Import and register route modules
from services.api.routes import jobs, resumes, match, rewrite, submit

app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(resumes.router, prefix="/api/resumes", tags=["resumes"])
app.include_router(match.router, prefix="/api/match", tags=["match"])
app.include_router(rewrite.router, prefix="/api/rewrite", tags=["rewrite"])
app.include_router(submit.router, prefix="/api/submit", tags=["submit"])
