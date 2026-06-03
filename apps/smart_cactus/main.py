"""
Mahsoul AI Agriculture Platform — FastAPI entry point.

Startup sequence:
  1. Configure structured logging
  2. Load TF model singleton (once, never per-request)
  3. Register middleware: CORS, request-id, timing, exception handling
  4. Mount versioned API routers
"""

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1 import assistant_routes, disease_routes, rag_routes
from app.core.config import settings
from app.core.logging import setup_logging
from app.models.ml.model_loader import ModelLoader
from app.rag.rag_service import RAGOrchestrator

logger = logging.getLogger(__name__)


# ── Lifespan (replaces on_event) ──────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info(
        "Starting up",
        extra={"app": settings.APP_NAME, "version": settings.APP_VERSION},
    )

    loader = ModelLoader.get_instance()
    await loader.initialize()

    try:
        await RAGOrchestrator.initialize()
        logger.info("RAG pipeline initialized (BGE-M3 + Qdrant + Redis)")
    except Exception as exc:
        logger.warning(
            "RAG pipeline failed to initialize — /rag/ask will return 503. "
            "Ensure Qdrant and Redis are running. Error: %s",
            exc,
        )

    logger.info("Startup complete — ready to serve requests")
    yield

    logger.info("Shutting down")
    await loader.cleanup()


# ── Application factory ───────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "**Mahsoul AI Agriculture Platform** — a scalable AI backend for:\n\n"
        "- Tomato disease detection (TF ensemble model)\n"
        "- AI farm assistant chat (LLM-ready)\n"
        "- RAG knowledge base for plant diseases (vector DB-ready)\n"
        "- Extensible for future CV / NLP services\n"
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ── Middleware ─────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=settings.ALLOWED_METHODS,
    allow_headers=settings.ALLOWED_HEADERS,
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    """Attach request-id + measure latency on every request."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    start = time.perf_counter()

    logger.info(
        "Incoming request",
        extra={"request_id": request_id, "method": request.method, "path": request.url.path},
    )

    response = await call_next(request)
    elapsed = round((time.perf_counter() - start) * 1000, 2)

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time-Ms"] = str(elapsed)

    logger.info(
        "Request finished",
        extra={
            "request_id": request_id,
            "status": response.status_code,
            "duration_ms": elapsed,
        },
    )
    return response


# ── Exception handlers ────────────────────────────────────────────────────────

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "data": None, "error": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "data": None,
            "error": "Validation error",
            "details": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "data": None,
            "error": str(exc) if settings.DEBUG else "Internal server error",
        },
    )


# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(disease_routes.router, prefix=settings.API_V1_PREFIX)
app.include_router(assistant_routes.router, prefix=settings.API_V1_PREFIX)
app.include_router(rag_routes.router, prefix=settings.API_V1_PREFIX)


# ── System endpoints ──────────────────────────────────────────────────────────

@app.get("/", tags=["System"])
async def root():
    return {
        "success": True,
        "data": {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs",
            "health": "/health",
        },
        "error": None,
    }


@app.get("/health", tags=["System"], summary="Health check with model & GPU status")
async def health_check():
    from app.utils.gpu_utils import get_gpu_info

    loader = ModelLoader.get_instance()
    gpu = get_gpu_info()

    return {
        "success": True,
        "data": {
            "status": "healthy",
            "model_loaded": loader.is_loaded,
            "model_name": settings.MODEL_NAME,
            "classes": len(loader.class_indices) if loader.is_loaded else 0,
            "gpu": gpu,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
        },
        "error": None,
    }
