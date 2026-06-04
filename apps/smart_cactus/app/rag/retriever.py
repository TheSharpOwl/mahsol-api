"""
Vector-store retriever abstraction.

Swap implementations by setting VECTOR_DB_URL in .env:
  - Empty / unset  →  MockRetriever (in-memory, for development)
  - Configured     →  ChromaDBRetriever (plug in real DB here)

To add Pinecone / Weaviate / FAISS, subclass BaseRetriever and update get_retriever().
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class BaseRetriever(ABC):
    @abstractmethod
    async def retrieve(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Return a list of document dicts sorted by relevance."""

    @abstractmethod
    async def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        """Persist documents (with pre-computed embeddings) to the store."""


# ── ChromaDB implementation ───────────────────────────────────────────────────

class ChromaDBRetriever(BaseRetriever):
    """
    ChromaDB retriever.

    Activate by:
      1. pip install chromadb
      2. Set VECTOR_DB_URL=http://localhost:8001 in .env
      3. Uncomment the chromadb lines below
    """

    def __init__(self, collection_name: str, host: str) -> None:
        self.collection_name = collection_name
        self.host = host
        self._client = None
        self._collection = None
        # TODO: uncomment once chromadb is installed
        # import chromadb
        # self._client = chromadb.HttpClient(host=host)
        # self._collection = self._client.get_or_create_collection(collection_name)

    async def retrieve(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        if self._collection is None:
            logger.warning("ChromaDB not configured — returning empty results")
            return []

        # results = self._collection.query(
        #     query_embeddings=[query_embedding],
        #     n_results=top_k,
        #     where=filters,
        # )
        # return self._format(results)
        return []

    async def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        if self._collection is None:
            logger.warning("ChromaDB not configured — skipping ingest")
            return

        # ids = [str(i) for i in range(len(documents))]
        # embeddings = [d.pop("embedding") for d in documents]
        # self._collection.add(
        #     ids=ids,
        #     embeddings=embeddings,
        #     documents=[d["content"] for d in documents],
        #     metadatas=[d.get("metadata", {}) for d in documents],
        # )

    @staticmethod
    def _format(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
        docs = []
        for content, meta, distance in zip(
            raw["documents"][0],
            raw["metadatas"][0],
            raw["distances"][0],
        ):
            docs.append({
                "content": content,
                "source": meta.get("source", ""),
                "score": 1.0 - distance,
                "metadata": meta,
            })
        return docs


# ── Mock implementation ───────────────────────────────────────────────────────

class MockRetriever(BaseRetriever):
    """In-memory retriever for local development — no vector DB required."""

    def __init__(self) -> None:
        self._docs: List[Dict[str, Any]] = []

    async def retrieve(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        return self._docs[:top_k]

    async def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        self._docs.extend(documents)
        logger.info(f"MockRetriever: stored {len(documents)} documents (total {len(self._docs)})")


# ── Factory ───────────────────────────────────────────────────────────────────

def get_retriever() -> BaseRetriever:
    from app.core.config import settings

    if settings.VECTOR_DB_URL:
        logger.info(f"Using ChromaDBRetriever at {settings.VECTOR_DB_URL}")
        return ChromaDBRetriever(
            collection_name=settings.VECTOR_DB_COLLECTION,
            host=settings.VECTOR_DB_URL,
        )

    logger.info("VECTOR_DB_URL not set — using MockRetriever")
    return MockRetriever()
