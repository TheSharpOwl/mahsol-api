"""
Text embedding abstraction.

Swap implementations by setting VECTOR_DB_URL in .env:
  - Empty / unset  →  MockEmbedder  (deterministic hash-based, for development)
  - Configured     →  SentenceTransformerEmbedder

To use OpenAI embeddings instead, subclass BaseEmbedder and update get_embedder().
"""

import hashlib
import logging
from abc import ABC, abstractmethod
from typing import List

logger = logging.getLogger(__name__)


class BaseEmbedder(ABC):
    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """Embed a single string."""

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of strings (more efficient than calling embed_text repeatedly)."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Output vector dimension."""


# ── SentenceTransformer implementation ────────────────────────────────────────

class SentenceTransformerEmbedder(BaseEmbedder):
    """
    SentenceTransformer embedder.

    Activate by:
      1. pip install sentence-transformers
      2. Set VECTOR_DB_URL in .env (triggers this path)
      3. Uncomment the sentence_transformers lines below
    """

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._model = None
        self._dim = 384  # all-MiniLM-L6-v2 default

        # TODO: uncomment once sentence-transformers is installed
        # from sentence_transformers import SentenceTransformer
        # self._model = SentenceTransformer(model_name)
        # self._dim = self._model.get_sentence_embedding_dimension()

    async def embed_text(self, text: str) -> List[float]:
        if self._model is None:
            logger.warning("SentenceTransformer not loaded — returning zero vector")
            return [0.0] * self._dim
        # return self._model.encode(text).tolist()
        return [0.0] * self._dim

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if self._model is None:
            return [[0.0] * self._dim for _ in texts]
        # return self._model.encode(texts).tolist()
        return [[0.0] * self._dim for _ in texts]

    @property
    def dimension(self) -> int:
        return self._dim


# ── Mock implementation ───────────────────────────────────────────────────────

class MockEmbedder(BaseEmbedder):
    """
    Deterministic hash-based embedder for local development.
    Produces consistent vectors for the same input — no ML model required.
    """

    _DIM = 384

    async def embed_text(self, text: str) -> List[float]:
        seed = int(hashlib.sha256(text.encode()).hexdigest(), 16)
        return [
            float((seed >> (i % 256)) & 0xFF) / 255.0
            for i in range(self._DIM)
        ]

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [await self.embed_text(t) for t in texts]

    @property
    def dimension(self) -> int:
        return self._DIM


# ── Factory ───────────────────────────────────────────────────────────────────

def get_embedder() -> BaseEmbedder:
    from app.core.config import settings

    if settings.VECTOR_DB_URL:
        logger.info(f"Using SentenceTransformerEmbedder: {settings.EMBEDDING_MODEL}")
        return SentenceTransformerEmbedder(settings.EMBEDDING_MODEL)

    logger.info("VECTOR_DB_URL not set — using MockEmbedder")
    return MockEmbedder()
