from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Mahsol API"
    version: str = "0.1.0"
    debug: bool = False
    # e.g. postgresql+psycopg://user:password@host:5432/dbname
    database_url: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
