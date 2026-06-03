"""
FastAPI dependency injection providers.

Import these in route handlers:
    from app.core.dependencies import DiseaseServiceDep, RAGServiceDep
"""

from typing import Annotated

from fastapi import Depends

from app.models.ml.model_loader import ModelLoader
from app.services.assistant_service import AssistantService
from app.services.disease_service import DiseaseService
from app.services.rag_service import RAGService


# ── Primitive providers ───────────────────────────────────────────────────────

def get_model_loader() -> ModelLoader:
    return ModelLoader.get_instance()


def get_disease_service(
    model_loader: Annotated[ModelLoader, Depends(get_model_loader)],
) -> DiseaseService:
    return DiseaseService(model_loader=model_loader)


def get_assistant_service() -> AssistantService:
    return AssistantService()


def get_rag_service() -> RAGService:
    from app.rag.rag_service import RAGOrchestrator
    from fastapi import HTTPException
    if RAGOrchestrator._instance is None:
        raise HTTPException(
            status_code=503,
            detail="RAG service unavailable — Qdrant and Redis must be running. Start them with: docker-compose up -d qdrant redis",
        )
    return RAGService()


# ── Typed aliases (use these in route signatures) ─────────────────────────────

ModelLoaderDep = Annotated[ModelLoader, Depends(get_model_loader)]
DiseaseServiceDep = Annotated[DiseaseService, Depends(get_disease_service)]
AssistantServiceDep = Annotated[AssistantService, Depends(get_assistant_service)]
RAGServiceDep = Annotated[RAGService, Depends(get_rag_service)]
