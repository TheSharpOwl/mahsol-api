from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "Farming Assistant API"
    DEBUG: bool = False

    # SQLite by default for local dev; override with MySQL in production via .env or docker-compose
    DATABASE_URL: str = "sqlite+aiosqlite:///./farming.db"
    DATABASE_URL_SYNC: str = "sqlite:///./farming.db"

    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    OPENWEATHER_API_KEY: Optional[str] = "cdc73c9756c6bddbaa7599a793e73401"
    OPENAI_API_KEY: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
