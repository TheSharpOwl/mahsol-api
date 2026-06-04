"""
Qdrant vector database — singleton, persistent collection.

Collection is created automatically on first use (idempotent).
HNSW index with cosine distance gives sub-millisecond search on
collections up to millions of vectors.

Payload stored per point:
  content       — raw chunk text (returned with search results)
  page_number   — PDF page (for citations)
  source        — filename or document title
  element_type  — "text" | "table" | "title"
  section_title — nearest section heading above this chunk
"""

import asyncio
import logging
import uuid
from threading import Lock
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    HnswConfigDiff,
    OptimizersConfigDiff,
    PointStruct,
    VectorParams,
)
from qdrant_client.http.exceptions import UnexpectedResponse

from app.core.config import settings

logger = logging.getLogger(__name__)


class QdrantVectorDB:
    _instance: Optional["QdrantVectorDB"] = None
    _lock: Lock = Lock()

    def __init__(self) -> None:
        self._client = QdrantClient(url=settings.QDRANT_URL, timeout=30)
        self._collection = settings.QDRANT_COLLECTION
        self._dim = settings.EMBEDDING_DIMENSION
        self._ensure_collection()

    # ── Singleton ─────────────────────────────────────────────────────────────

    @classmethod
    def get_instance(cls) -> "QdrantVectorDB":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ── Public async API ──────────────────────────────────────────────────────

    async def upsert(
        self,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]],
    ) -> int:
        """Store chunk texts + embeddings. Returns number of points upserted."""
        points = []
        for chunk, vector in zip(chunks, embeddings):
            meta = chunk.get("metadata", {})
            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload={
                        "content": chunk["content"],
                        "page_number": meta.get("page_number"),
                        "source": meta.get("source", ""),
                        "element_type": meta.get("element_type", "text"),
                        "section_title": meta.get("section_title"),
                    },
                )
            )

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._client.upsert(
                collection_name=self._collection,
                points=points,
            ),
        )
        logger.info("Upserted %d points to collection '%s'", len(points), self._collection)
        return len(points)

    async def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Cosine similarity search. Returns top_k results with payload + score."""
        from qdrant_client.http.models import Filter, FieldCondition, MatchValue

        qdrant_filter = None
        if filters:
            conditions = [
                FieldCondition(key=k, match=MatchValue(value=v))
                for k, v in filters.items()
            ]
            qdrant_filter = Filter(must=conditions)

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self._client.query_points(
                collection_name=self._collection,
                query=query_vector,
                query_filter=qdrant_filter,
                limit=top_k,
                with_payload=True,
            ),
        )
        results = response.points

        return [
            {
                "content": r.payload.get("content", ""),
                "score": r.score,
                "page_number": r.payload.get("page_number"),
                "source": r.payload.get("source", ""),
                "element_type": r.payload.get("element_type", "text"),
                "section_title": r.payload.get("section_title"),
            }
            for r in results
        ]

    async def collection_info(self) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(
            None,
            lambda: self._client.get_collection(self._collection),
        )
        count = getattr(info, "points_count", None) or getattr(info, "vectors_count", 0)
        return {
            "name": self._collection,
            "vectors_count": count,
            "status": str(info.status),
        }

    # ── Private ───────────────────────────────────────────────────────────────

    def _ensure_collection(self) -> None:
        """Create collection if it doesn't exist. Safe to call multiple times."""
        try:
            self._client.get_collection(self._collection)
            logger.info("Qdrant collection '%s' already exists", self._collection)
        except (UnexpectedResponse, Exception):
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(
                    size=self._dim,
                    distance=Distance.COSINE,
                ),
                hnsw_config=HnswConfigDiff(
                    m=16,
                    ef_construct=200,
                    full_scan_threshold=10000,
                ),
                optimizers_config=OptimizersConfigDiff(
                    indexing_threshold=20000,
                ),
            )
            logger.info(
                "Created Qdrant collection '%s' (dim=%d, cosine)",
                self._collection,
                self._dim,
            )
