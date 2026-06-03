"""
RAG service layer — thin FastAPI adapter over RAGOrchestrator.

This layer exists to match the existing dependency-injection pattern used
by the rest of the codebase (disease_service, assistant_service). All real
RAG logic lives in app/rag/rag_service.py (the orchestrator).
"""

import logging
from typing import Any, Dict, List, Optional

from app.rag.rag_service import RAGOrchestrator

logger = logging.getLogger(__name__)


class RAGService:
    def __init__(self) -> None:
        self._orchestrator = RAGOrchestrator.get_instance()

    async def ask(
        self,
        user_id: str,
        question: str,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        result = await self._orchestrator.ask(
            user_id=user_id,
            question=question,
            top_k=top_k,
        )
        return {
            "answer": result.answer,
            "sources": result.sources,
            "retrieved_chunks": result.retrieved_chunks,
            "tokens_used": result.tokens_used,
            "model": result.model,
        }

    async def get_history(self, user_id: str) -> List[Dict[str, Any]]:
        return await self._orchestrator.get_history(user_id)

    async def clear_history(self, user_id: str) -> None:
        await self._orchestrator.clear_history(user_id)

    async def ingest_pdf(self, pdf_path: Optional[str] = None) -> Dict[str, Any]:
        from app.core.config import settings
        path = pdf_path or settings.PDF_PATH
        result = await self._orchestrator.ingest_pdf(path)
        return {
            "chunks_ingested": result.chunks_ingested,
            "source": result.source,
            "errors": result.errors,
        }
