import os
from pydantic_settings import BaseSettings
from typing import Optional



class Settings(BaseSettings):
    APP_NAME: str = "Farming Assistant API"
    DEBUG: bool = False
    # connect to the online MySQL database by default, but allow overriding with SQLite for local development if needed
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./farming.db")
    DATABASE_URL_SYNC: str = os.getenv("DATABASE_URL_SYNC", "sqlite:///./farming.db")

    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALGORITHM: str = os.getenv("ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 # 1 day

    OPENWEATHER_API_KEY: Optional[str] = os.getenv("OPENWEATHER_API_KEY")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")

    class Config:
        env_file = ".env"
        case_sensitive = True
        # ignore any extra environment variables that are not defined in this settings class
        extra = "ignore"


settings = Settings()
