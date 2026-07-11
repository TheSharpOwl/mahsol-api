from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup once a database is configured
    if settings.database_url:
        from app.core.db import Base, get_engine

        Base.metadata.create_all(bind=get_engine())
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    lifespan=lifespan,
)

app.include_router(router, prefix="/api/v1")


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
