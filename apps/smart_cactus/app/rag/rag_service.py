"""
RAG Orchestrator — the central brain of the retrieval pipeline.

Responsibilities:
  1. Accept (user_id, question) from the FastAPI layer
  2. Load user's conversation history from Redis
  3. Retrieve relevant chunks from Qdrant via BGE-M3 similarity search
  4. Generate a grounded answer via OpenAI gpt-4o-mini
  5. Persist the new Q&A turn to Redis
  6. Return a structured RAGAnswer (answer + sources + metadata)

Singleton pattern: all heavy components (embedder, vector_db, retriever,
memory, generator) are singletons initialized at server startup.
The orchestrator itself is also a singleton so all requests share the
same pre-warmed components.

Data flow:
  user_id + question
       │
       ├─► RedisChatMemory.get_history()      → List[{role, content}]
       │
       ├─► RAGRetriever.retrieve()            → List[RetrievedChunk]
       │       └─ BGEEmbedder.embed_query()
       │       └─ QdrantVectorDB.search()
       │
       ├─► OpenAIGenerator.generate()         → GenerationResult
       │       └─ builds: system + history + context + question
       │       └─ calls: gpt-4o-mini
       │
       ├─► RedisChatMemory.add_message(user)
       ├─► RedisChatMemory.add_message(assistant)
       │
       └─► RAGAnswer(answer, sources, chunks, tokens_used)
"""

import logging
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.rag.embeddings.embedding_model import BGEEmbedder
from app.rag.generator.openai_generator import OpenAIGenerator
from app.rag.ingest.pdf_ingest import PDFIngestor
from app.rag.memory.chat_memory import RedisChatMemory
from app.rag.retriever.retriever import RAGRetriever, RetrievedChunk
from app.rag.vectordb.qdrant_client import QdrantVectorDB

logger = logging.getLogger(__name__)


@dataclass
class RAGAnswer:
    answer: str
    sources: List[Dict[str, Any]]
    retrieved_chunks: List[Dict[str, Any]]
    tokens_used: int
    model: str


@dataclass
class IngestResult:
    chunks_ingested: int
    source: str
    errors: List[str] = field(default_factory=list)


class RAGOrchestrator:
    _instance: Optional["RAGOrchestrator"] = None
    _lock: Lock = Lock()

    def __init__(
        self,
        embedder: BGEEmbedder,
        vector_db: QdrantVectorDB,
        retriever: RAGRetriever,
        memory: RedisChatMemory,
        generator: OpenAIGenerator,
    ) -> None:
        self._embedder = embedder
        self._vector_db = vector_db
        self._retriever = retriever
        self._memory = memory
        self._generator = generator

    # ── Singleton (assembled at startup via initialize()) ─────────────────────

    @classmethod
    async def initialize(cls) -> "RAGOrchestrator":
        """
        Build and wire all RAG components.
        Called once from app/main.py lifespan startup.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    embedder = BGEEmbedder.get_instance()
                    vector_db = QdrantVectorDB.get_instance()
                    retriever = RAGRetriever(embedder, vector_db)
                    memory = await RedisChatMemory.get_instance()
                    generator = OpenAIGenerator()

                    cls._instance = cls(
                        embedder=embedder,
                        vector_db=vector_db,
                        retriever=retriever,
                        memory=memory,
                        generator=generator,
                    )
                    logger.info("RAGOrchestrator initialized")
        return cls._instance

    @classmethod
    def get_instance(cls) -> "RAGOrchestrator":
        if cls._instance is None:
            raise RuntimeError(
                "RAGOrchestrator not initialized. "
                "Call await RAGOrchestrator.initialize() in app lifespan."
            )
        return cls._instance

    # ── Public API ────────────────────────────────────────────────────────────

    async def ask(
        self,
        user_id: str,
        question: str,
        top_k: int = None,
    ) -> RAGAnswer:
        """
        Full RAG pipeline for one user question.

        Args:
            user_id: any string — unknown IDs start fresh history automatically.
            question: user's question in Arabic or English.
            top_k: number of chunks to retrieve (defaults to settings.RAG_TOP_K).
        """
        top_k = top_k or settings.RAG_TOP_K

        # 1. Load conversation history
        history = await self._memory.get_history_for_llm(user_id)
        logger.debug("User '%s': loaded %d history messages", user_id, len(history))

        # 2. Retrieve relevant chunks
        chunks: List[RetrievedChunk] = await self._retriever.retrieve(
            query=question,
            top_k=top_k,
        )
        logger.info(
            "User '%s': retrieved %d chunks (best score=%.3f)",
            user_id,
            len(chunks),
            chunks[0].score if chunks else 0.0,
        )

        # 3. Generate answer
        result = await self._generator.generate(
            question=question,
            context_chunks=chunks,
            history=history,
        )

        # 4. Persist conversation turn
        await self._memory.add_message(user_id, "user", question)
        await self._memory.add_message(user_id, "assistant", result.answer)

        # 5. Build response
        sources = [c.to_dict() for c in chunks]
        return RAGAnswer(
            answer=result.answer,
            sources=sources,
            retrieved_chunks=sources,
            tokens_used=result.tokens_used,
            model=result.model,
        )

    async def get_history(self, user_id: str) -> List[Dict[str, Any]]:
        return await self._memory.get_history(user_id)

    async def clear_history(self, user_id: str) -> None:
        await self._memory.clear_history(user_id)

    async def ingest_pdf(self, pdf_path: str) -> IngestResult:
        """
        Ingest a PDF into Qdrant. Called from the admin /ingest endpoint
        or from run_ingest.py CLI.
        """
        errors: List[str] = []
        try:
            ingestor = PDFIngestor()
            chunks = ingestor.load_and_chunk(pdf_path)
        except FileNotFoundError as exc:
            return IngestResult(chunks_ingested=0, source=pdf_path, errors=[str(exc)])

        try:
            texts = [c["content"] for c in chunks]
            embeddings = await self._embedder.embed_batch(texts)
            upserted = await self._vector_db.upsert(chunks, embeddings)
        except Exception as exc:
            logger.error("Ingest failed: %s", exc, exc_info=True)
            errors.append(str(exc))
            upserted = 0

        return IngestResult(
            chunks_ingested=upserted,
            source=pdf_path,
            errors=errors,
        )
