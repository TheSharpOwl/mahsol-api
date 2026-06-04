"""
Disease prediction service.

Orchestrates:
  1. Image validation
  2. Async preprocessing (thread pool)
  3. Async model inference (thread pool)
  4. Result mapping & ranking
"""

import logging
from typing import Any, Dict, List

import numpy as np

from app.core.config import settings
from app.models.ml.model_loader import ModelLoader
from app.utils.image_preprocessing import preprocess_image_async, validate_image

logger = logging.getLogger(__name__)


class DiseaseService:
    def __init__(self, model_loader: ModelLoader) -> None:
        self._loader = model_loader

    async def predict_disease(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Full prediction pipeline for a single image.

        Returns a dict that matches the DiseasePredictionResponse schema exactly.
        """
        # ── 1. Validate ───────────────────────────────────────────────────────
        validate_image(image_bytes)

        # ── 2. Preprocess ─────────────────────────────────────────────────────
        preprocessed = await preprocess_image_async(image_bytes)  # (1, 224, 224, 3)

        # ── 3. Inference ──────────────────────────────────────────────────────
        raw: np.ndarray = await self._loader.predict(preprocessed)
        probabilities: np.ndarray = raw[0]  # (num_classes,)

        # ── 4. Map → class names ──────────────────────────────────────────────
        all_scores = self._map_probabilities(probabilities)

        # ── 5. Sort & slice ───────────────────────────────────────────────────
        sorted_preds: List[tuple] = sorted(
            all_scores.items(), key=lambda x: x[1], reverse=True
        )

        top_disease, top_confidence = sorted_preds[0]
        top_k = [
            {"disease": d, "confidence": round(float(c), 6)}
            for d, c in sorted_preds[: settings.TOP_K_PREDICTIONS]
        ]
        all_scores_rounded = {k: round(float(v), 6) for k, v in all_scores.items()}

        logger.info(
            "Prediction complete",
            extra={"disease": top_disease, "confidence": round(float(top_confidence), 4)},
        )

        return {
            "success": True,
            "prediction": {
                "disease": top_disease,
                "confidence": round(float(top_confidence), 6),
                "top_predictions": top_k,
                "all_scores": all_scores_rounded,
            },
            "model": settings.MODEL_NAME,
        }

    # ── Private ───────────────────────────────────────────────────────────────

    def _map_probabilities(self, probabilities: np.ndarray) -> Dict[str, float]:
        return {
            self._loader.index_to_class[i]: float(probabilities[i])
            for i in range(len(probabilities))
            if i in self._loader.index_to_class
        }
