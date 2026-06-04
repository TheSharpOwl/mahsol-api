"""
BGE-M3 embedding model — singleton, async-safe.

Why BAAI/bge-m3:
  - Multilingual (100+ languages): handles Arabic and English in the same vector space
  - 1024-dim dense vectors: richer semantic space than 384-dim MiniLM
  - MTEB top-ranked for retrieval tasks on technical domain content
  - Single model supports both indexing (passages) and querying

Singleton pattern: the model is heavy (~2 GB), loaded once at server startup,
reused across all requests. Inference runs in a ThreadPoolExecutor so the
asyncio event loop is never blocked.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from typing import List, Optional

from sentence_transformers import SentenceTransformer

from app.core.config import settings

logger = logging.getLogger(__name__)

_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


class BGEEmbedder:
    DIMENSION = 1024

    _instance: Optional["BGEEmbedder"] = None
    _lock: Lock = Lock()

    def __init__(self) -> None:
        logger.info("Loading BGE-M3 embedding model — this takes ~30 s on first load")
        self._model = SentenceTransformer(
            settings.EMBEDDING_MODEL,
            trust_remote_code=True,
        )
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="bge")
        logger.info("BGE-M3 loaded (dim=%d)", self.DIMENSION)

    # ── Singleton ─────────────────────────────────────────────────────────────

    @classmethod
    def get_instance(cls) -> "BGEEmbedder":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ── Public async API ──────────────────────────────────────────────────────

    async def embed_text(self, text: str) -> List[float]:
        """Embed a passage (document chunk) — no instruction prefix."""
        return await self._run([text], normalize=True)

    async def embed_query(self, query: str) -> List[float]:
        """Embed a retrieval query — prepends BGE instruction prefix."""
        prefixed = _QUERY_PREFIX + query
        return await self._run([prefixed], normalize=True)

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Batch-embed document passages. Use for ingestion."""
        loop = asyncio.get_event_loop()
        vectors = await loop.run_in_executor(
            self._executor,
            lambda: self._model.encode(
                texts,
                normalize_embeddings=True,
                batch_size=32,
                show_progress_bar=False,
            ).tolist(),
        )
        return vectors

    # ── Private ───────────────────────────────────────────────────────────────

    async def _run(self, texts: List[str], normalize: bool) -> List[float]:
        loop = asyncio.get_event_loop()
        vectors = await loop.run_in_executor(
            self._executor,
            lambda: self._model.encode(
                texts,
                normalize_embeddings=normalize,
                show_progress_bar=False,
            ).tolist(),
        )
        return vectors[0]
