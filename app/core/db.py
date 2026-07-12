import certifi
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


_engine = None
_session_factory = None


def get_engine():
    global _engine
    if _engine is None:
        if not settings.database_url:
            raise HTTPException(status_code=503, detail="Database is not configured")
        url = settings.database_url
        # psycopg's bundled libpq can't read the OS cert store that
        # sslrootcert=system refers to; substitute certifi's CA bundle
        if "sslrootcert=system" in url:
            url = url.replace("sslrootcert=system", f"sslrootcert={certifi.where()}")
        _engine = create_engine(url, pool_pre_ping=True)
    return _engine


def get_db():
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), autoflush=False)
    db = _session_factory()
    try:
        yield db
    finally:
        db.close()
