"""
Image preprocessing pipeline.

CRITICAL: This pipeline MUST match the Albumentations Normalize transform
used during training:

    Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225))

Pipeline order:
  1. Decode bytes → PIL Image → RGB
  2. Resize to (224, 224) with LANCZOS filter
  3. Convert to float32 numpy array
  4. Scale to [0, 1]  →  img / 255.0
  5. ImageNet normalize  →  (img - mean) / std
  6. Expand batch dimension  →  shape (1, 224, 224, 3)
"""

import asyncio
import io
import logging
from typing import Tuple

import numpy as np
from PIL import Image, UnidentifiedImageError

from app.core.config import settings

logger = logging.getLogger(__name__)

_MEAN: np.ndarray = np.array(settings.NORMALIZE_MEAN, dtype=np.float32)  # (3,)
_STD: np.ndarray = np.array(settings.NORMALIZE_STD, dtype=np.float32)    # (3,)
_TARGET: Tuple[int, int] = (settings.IMAGE_SIZE, settings.IMAGE_SIZE)


# ── Public API ────────────────────────────────────────────────────────────────

def preprocess_image_bytes(image_bytes: bytes) -> np.ndarray:
    """
    Synchronous preprocessing — runs in ThreadPoolExecutor.
    Returns array with shape (1, IMAGE_SIZE, IMAGE_SIZE, 3).
    """
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image = image.resize(_TARGET, Image.LANCZOS)

    arr = np.array(image, dtype=np.float32)  # (H, W, 3)  uint8 values 0-255
    arr /= 255.0                              # scale to [0, 1]
    arr = (arr - _MEAN) / _STD               # Albumentations Normalize

    return np.expand_dims(arr, axis=0)       # (1, H, W, 3)


async def preprocess_image_async(image_bytes: bytes) -> np.ndarray:
    """Async wrapper — offloads CPU-bound preprocessing to thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, preprocess_image_bytes, image_bytes)


def validate_image(image_bytes: bytes, max_size_mb: float | None = None) -> None:
    """
    Validate raw image bytes before preprocessing.
    Raises ValueError on failure — caller should convert to HTTP 400.
    """
    max_mb = max_size_mb if max_size_mb is not None else settings.MAX_IMAGE_SIZE_MB

    size_mb = len(image_bytes) / (1024 * 1024)
    if size_mb > max_mb:
        raise ValueError(
            f"Image size {size_mb:.2f} MB exceeds the {max_mb} MB limit."
        )

    if len(image_bytes) == 0:
        raise ValueError("Received an empty file.")

    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.verify()
    except UnidentifiedImageError:
        raise ValueError("Cannot identify image file. Upload a JPEG, PNG, or WebP.")
    except Exception as exc:
        raise ValueError(f"Invalid image: {exc}")
