from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.core.config import settings
from app.api.routes import auth, land_info, conversations, reports, chat

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Farming Assistant API...")
    from app.db.session import async_engine
    from app.db.base import Base
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified")
    yield
    logger.info("Shutting down Farming Assistant API")
    await async_engine.dispose()


app = FastAPI(
    title="Farming Assistant API",
    description=(
        "AI-powered farming assistant backend. Helps farmers diagnose crop diseases, "
        "interact with an AI chatbot, and receive daily reports based on weather and land data."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(land_info.router)
app.include_router(conversations.router)
app.include_router(reports.router)
app.include_router(chat.router)


@app.get("/healthz", tags=["Health"])
async def health_check():
    return {"status": "ok", "service": settings.APP_NAME}
