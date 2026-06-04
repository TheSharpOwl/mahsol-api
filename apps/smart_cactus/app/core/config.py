import os

from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    # ── Application ──────────────────────────────────────────────────────────
    APP_NAME: str = "Mahsoul AI Agriculture Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"  # development | staging | production

    # ── API ───────────────────────────────────────────────────────────────────
    API_V1_PREFIX: str = "/api/v1"

    # ── CORS ──────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: List[str] = ["*"]
    ALLOWED_METHODS: List[str] = ["*"]
    ALLOWED_HEADERS: List[str] = ["*"]

    # ── Model Paths ───────────────────────────────────────────────────────────
    MODEL_PATH: str = str(
        BASE_DIR / "app" / "models" / "ml" / "mahsoul_production_model.h5"
    )
    CLASS_INDICES_PATH: str = str(
        BASE_DIR / "app" / "models" / "ml" / "class_indices.json"
    )
    MODEL_NAME: str = "Mahsoul_Ensemble_v3"

    # Public URL source for model artifacts (no credentials required).
    # If set, these are downloaded to MODEL_PATH and CLASS_INDICES_PATH.
    MODEL_PUBLIC_URL: str = os.getenv("MODEL_PUBLIC_URL", "")
    # ── Image Preprocessing  (must match Albumentations training pipeline) ────
    IMAGE_SIZE: int = 224
    NORMALIZE_MEAN: List[float] = [0.485, 0.456, 0.406]
    NORMALIZE_STD: List[float] = [0.229, 0.224, 0.225]

    # ── Inference Settings ────────────────────────────────────────────────────
    TOP_K_PREDICTIONS: int = 3
    CONFIDENCE_THRESHOLD: float = 0.0
    MAX_IMAGE_SIZE_MB: float = 10.0
    INFERENCE_WORKERS: int = 2  # ThreadPoolExecutor workers for model inference

    # ── GPU ───────────────────────────────────────────────────────────────────
    GPU_MEMORY_GROWTH: bool = True
    MIXED_PRECISION: bool = False  # Enable for GPUs with good FP16 support (Ampere+)

    # ── Logging ───────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json | text

    # ── Qdrant Vector Database ────────────────────────────────────────────────
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "tomato_knowledge"

    # ── Embeddings ────────────────────────────────────────────────────────────
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    EMBEDDING_DIMENSION: int = 1024  # BGE-M3 output dimension

    # ── OpenAI ────────────────────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_MAX_TOKENS: int = 1024
    OPENAI_TEMPERATURE: float = 0.3  # low temp for factual agriculture answers

    # ── Redis (chat history) ──────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379"
    MAX_CHAT_HISTORY: int = 10      # max messages stored per user (5 turns)
    CHAT_HISTORY_TTL: int = 604800  # 7 days in seconds

    # ── RAG Pipeline ──────────────────────────────────────────────────────────
    PDF_PATH: str = "data/tomato_knowledge.pdf"
    RAG_TOP_K: int = 5

    model_config = {"env_file": ".env", "case_sensitive": True}


settings = Settings()
