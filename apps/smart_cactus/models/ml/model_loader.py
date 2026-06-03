"""
Singleton TensorFlow model loader.

Design guarantees:
- Model loaded exactly once at startup via initialize()
- Thread-safe singleton via double-checked locking
- Async inference via ThreadPoolExecutor (never blocks event loop)
- Warmup pass eliminates first-request latency spike
"""

import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock
from typing import Dict, Optional

import numpy as np

logger = logging.getLogger(__name__)


class ModelLoader:
    _instance: Optional["ModelLoader"] = None
    _class_lock: Lock = Lock()

    def __init__(self) -> None:
        self.model = None
        self.class_indices: Dict[str, str] = {}
        self.index_to_class: Dict[int, str] = {}
        self.is_loaded: bool = False
        self._executor: Optional[ThreadPoolExecutor] = None

    # ── Singleton ─────────────────────────────────────────────────────────────

    @classmethod
    def get_instance(cls) -> "ModelLoader":
        if cls._instance is None:
            with cls._class_lock:
                if cls._instance is None:
                    cls._instance = ModelLoader()
        return cls._instance

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        if self.is_loaded:
            return

        from app.core.config import settings

        self._executor = ThreadPoolExecutor(
            max_workers=settings.INFERENCE_WORKERS,
            thread_name_prefix="tf_inference",
        )

        await self._configure_gpu()

        model_path = Path(settings.MODEL_PATH)
        class_path = Path(settings.CLASS_INDICES_PATH)

        if not model_path.exists():
            raise FileNotFoundError(
                f"Model not found: {model_path}\n"
                "Place mahsoul_production_model.h5 in app/models/ml/"
            )
        if not class_path.exists():
            raise FileNotFoundError(
                f"Class indices not found: {class_path}\n"
                "Place class_indices.json in app/models/ml/"
            )

        logger.info(f"Loading model: {model_path}")
        loop = asyncio.get_event_loop()

        self.model = await loop.run_in_executor(
            self._executor,
            lambda: self._load_model(str(model_path)),
        )

        with open(class_path, "r", encoding="utf-8") as f:
            self.class_indices = json.load(f)

        self.index_to_class = {int(k): v for k, v in self.class_indices.items()}

        await self._warmup()

        self.is_loaded = True
        logger.info(
            "Model ready",
            extra={"classes": len(self.class_indices), "model": settings.MODEL_NAME},
        )

    async def cleanup(self) -> None:
        self.model = None
        self.is_loaded = False
        if self._executor:
            self._executor.shutdown(wait=False)
        logger.info("Model resources released")

    # ── Inference ─────────────────────────────────────────────────────────────

    async def predict(self, preprocessed: np.ndarray) -> np.ndarray:
        if not self.is_loaded or self.model is None:
            raise RuntimeError("Model is not loaded. Call initialize() first.")

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor,
            lambda: self.model(preprocessed, training=False).numpy(),
        )
        return result

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _load_model(path: str):
        import keras
        return keras.models.load_model(path, compile=False, safe_mode=False)

    async def _configure_gpu(self) -> None:
        from app.core.config import settings

        try:
            import tensorflow as tf

            gpus = tf.config.list_physical_devices("GPU")
            if gpus:
                for gpu in gpus:
                    tf.config.experimental.set_memory_growth(gpu, settings.GPU_MEMORY_GROWTH)
                logger.info(f"GPU configured: {len(gpus)} device(s) found")
            else:
                logger.info("No GPU detected — running on CPU")

        except Exception as exc:
            logger.warning(f"GPU configuration skipped: {exc}")

    async def _warmup(self) -> None:
        try:
            dummy = np.zeros((1, 224, 224, 3), dtype=np.float32)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self._executor,
                lambda: self.model(dummy, training=False),
            )
            logger.info("Model warmup completed")
        except Exception as exc:
            logger.warning(f"Model warmup failed (non-fatal): {exc}")
