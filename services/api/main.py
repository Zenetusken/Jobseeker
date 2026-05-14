"""
Jobseeker Orchestrator — FastAPI Backend
Central API that connects Streamlit frontend to vLLM, Qdrant, and Celery.
"""
import time
import collections
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger

from config.settings import settings
from services.qdrant.init_collections import init_collections
from services.api.security import get_api_key


# ---------------------------------------------------------------------------
# Security headers middleware
# ---------------------------------------------------------------------------

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach hardening headers to every response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cache-Control"] = "no-store"
        return response


# ---------------------------------------------------------------------------
# In-process rate limiter middleware
# ---------------------------------------------------------------------------

# Route-specific limits: (max_requests, window_seconds)
_RATE_LIMITS: dict[tuple[str, str], tuple[int, int]] = {
    ("POST", "/api/rewrite/tailor"): (10, 60),
    ("POST", "/api/submit/apply"): (5, 60),
    ("POST", "/api/resumes/upload"): (30, 60),
    ("POST", "/api/jobs/ingest"): (60, 60),
    ("POST", "/api/jobs/ingest/batch"): (10, 60),
    ("POST", "/api/jobs/ingest/file"): (20, 60),
}

# {(ip, method, path): deque of timestamps}
_request_log: dict = collections.defaultdict(collections.deque)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple sliding-window rate limiter keyed by (client IP, method, path)."""

    async def dispatch(self, request: Request, call_next) -> Response:
        key = (request.method, request.url.path)
        limit_cfg = _RATE_LIMITS.get(key)
        if limit_cfg is None:
            return await call_next(request)

        max_requests, window = limit_cfg
        client_ip = request.client.host if request.client else "unknown"
        log_key = (client_ip, request.method, request.url.path)
        now = time.monotonic()
        timestamps = _request_log[log_key]

        # Evict old entries outside the window
        while timestamps and timestamps[0] < now - window:
            timestamps.popleft()

        if len(timestamps) >= max_requests:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please slow down."},
                headers={"Retry-After": str(window)},
            )

        timestamps.append(now)
        return await call_next(request)


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialize Qdrant collections. Shutdown: cleanup."""
    logger.info("=== Jobseeker Orchestrator Starting ===")
    logger.info(f"vLLM endpoint: {settings.vllm_base_url}")
    logger.info(f"Qdrant endpoint: {settings.qdrant_url}")
    logger.info(f"Auth enabled: {bool(settings.api_key)}")
    logger.info(f"Debug / Swagger UI: {settings.api_debug}")
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
    docs_url="/docs" if settings.api_debug else None,
    redoc_url="/redoc" if settings.api_debug else None,
    openapi_url="/openapi.json" if settings.api_debug else None,
)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list or [],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["X-API-Key", "Content-Type"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "orchestrator"}


# ---------------------------------------------------------------------------
# Route registration — all protected by API key dependency
# ---------------------------------------------------------------------------

from services.api.routes import jobs, resumes, match, rewrite, submit

_auth = [Depends(get_api_key)]

app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"], dependencies=_auth)
app.include_router(resumes.router, prefix="/api/resumes", tags=["resumes"], dependencies=_auth)
app.include_router(match.router, prefix="/api/match", tags=["match"], dependencies=_auth)
app.include_router(rewrite.router, prefix="/api/rewrite", tags=["rewrite"], dependencies=_auth)
app.include_router(submit.router, prefix="/api/submit", tags=["submit"], dependencies=_auth)
