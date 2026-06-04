import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.dependencies import get_rag_service
from app.schemas.rag_schema import (
    ChatMessage,
    RAGAskRequest,
    RAGAskResponse,
    RAGHistoryResponse,
    RAGIngestRequest,
    RAGIngestResponse,
    SourceDocument,
)
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["RAG Knowledge Base"])


@router.post(
    "/ask",
    response_model=RAGAskResponse,
    summary="Ask the Tomato Knowledge Base",
    description=(
        "Send a question (Arabic or English) and get a grounded answer "
        "from the tomato disease knowledge base. "
        "Conversation history is automatically maintained per user_id in Redis."
    ),
)
async def ask(
    body: RAGAskRequest,
    rag_service: RAGService = Depends(get_rag_service),
) -> JSONResponse:
    try:
        result = await rag_service.ask(
            user_id=body.user_id,
            question=body.question,
            top_k=body.top_k,
        )
    except RuntimeError as exc:
        logger.error("RAG service not initialized: %s", exc)
        raise HTTPException(status_code=503, detail="RAG service unavailable — check server startup logs")
    except Exception:
        logger.error("RAG ask error", exc_info=True)
        raise HTTPException(status_code=500, detail="RAG pipeline failed")

    sources = [
        SourceDocument(
            content=s["content"],
            page_number=s.get("page_number"),
            source=s.get("source", ""),
            section_title=s.get("section_title"),
            element_type=s.get("element_type", "text"),
            relevance_score=s.get("score", 0.0),
        )
        for s in result["sources"]
    ]

    return JSONResponse(
        content=RAGAskResponse(
            success=True,
            answer=result["answer"],
            sources=sources,
            tokens_used=result["tokens_used"],
            model=result["model"],
        ).model_dump()
    )


@router.post(
    "/ingest",
    response_model=RAGIngestResponse,
    summary="Ingest PDF into Knowledge Base",
    description=(
        "Trigger PDF ingestion. Parses the PDF, embeds chunks via BGE-M3, "
        "and upserts to Qdrant. Use pdf_path to override the default path from .env."
    ),
)
async def ingest(
    body: RAGIngestRequest,
    rag_service: RAGService = Depends(get_rag_service),
) -> JSONResponse:
    try:
        result = await rag_service.ingest_pdf(pdf_path=body.pdf_path)
    except Exception:
        logger.error("RAG ingest error", exc_info=True)
        raise HTTPException(status_code=500, detail="Ingestion failed")

    success = result["chunks_ingested"] > 0 and not result["errors"]
    return JSONResponse(
        content=RAGIngestResponse(
            success=success,
            chunks_ingested=result["chunks_ingested"],
            source=result["source"],
            errors=result["errors"],
        ).model_dump()
    )


@router.get(
    "/history/{user_id}",
    response_model=RAGHistoryResponse,
    summary="Get Chat History",
    description="Retrieve stored conversation history for a user_id from Redis.",
)
async def get_history(
    user_id: str,
    rag_service: RAGService = Depends(get_rag_service),
) -> JSONResponse:
    try:
        messages = await rag_service.get_history(user_id)
    except Exception:
        logger.error("RAG get_history error", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not fetch history")

    return JSONResponse(
        content=RAGHistoryResponse(
            success=True,
            user_id=user_id,
            messages=[ChatMessage(**m) for m in messages],
            total=len(messages),
        ).model_dump()
    )


@router.delete(
    "/history/{user_id}",
    summary="Clear Chat History",
    description="Delete all stored conversation history for a user_id from Redis.",
)
async def clear_history(
    user_id: str,
    rag_service: RAGService = Depends(get_rag_service),
) -> JSONResponse:
    try:
        await rag_service.clear_history(user_id)
    except Exception:
        logger.error("RAG clear_history error", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not clear history")

    return JSONResponse(
        content={"success": True, "user_id": user_id, "message": "History cleared", "error": None}
    )
