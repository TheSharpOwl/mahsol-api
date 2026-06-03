"""
Retrieval pipeline — embed query → search Qdrant → return ranked chunks.

Retrieval flow:
  1. embed_query(text) — BGE-M3 with retrieval instruction prefix
     (the prefix shifts the vector toward "find passages that answer this")
  2. vector_db.search() — cosine ANN search in Qdrant HNSW index
  3. Wrap raw Qdrant results into typed RetrievedChunk dataclass
  4. Return sorted by score descending (Qdrant already sorts, but we re-sort
     defensively in case of future filter post-processing)
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.rag.embeddings.embedding_model import BGEEmbedder
from app.rag.vectordb.qdrant_client import QdrantVectorDB

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    content: str
    score: float
    page_number: Optional[int]
    source: str
    element_type: str
    section_title: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "score": round(self.score, 4),
            "page_number": self.page_number,
            "source": self.source,
            "element_type": self.element_type,
            "section_title": self.section_title,
        }


class RAGRetriever:
    def __init__(self, embedder: BGEEmbedder, vector_db: QdrantVectorDB) -> None:
        self._embedder = embedder
        self._vector_db = vector_db

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievedChunk]:
        """
        Full retrieval pipeline for one user query.

        Args:
            query: raw user question (Arabic or English)
            top_k: number of chunks to return
            filters: optional Qdrant payload filters, e.g. {"element_type": "table"}

        Returns:
            List of RetrievedChunk sorted by relevance score descending.
        """
        query_vector = await self._embedder.embed_query(query)

        raw_results = await self._vector_db.search(
            query_vector=query_vector,
            top_k=top_k,
            filters=filters,
        )

        chunks = [
            RetrievedChunk(
                content=r["content"],
                score=r["score"],
                page_number=r.get("page_number"),
                source=r.get("source", ""),
                element_type=r.get("element_type", "text"),
                section_title=r.get("section_title"),
            )
            for r in raw_results
        ]

        chunks.sort(key=lambda c: c.score, reverse=True)

        logger.debug(
            "Retrieved %d chunks for query (top score=%.3f)",
            len(chunks),
            chunks[0].score if chunks else 0.0,
        )
        return chunks

    @classmethod
    def get_instance(cls) -> "RAGRetriever":
        return cls(
            embedder=BGEEmbedder.get_instance(),
            vector_db=QdrantVectorDB.get_instance(),
        )
