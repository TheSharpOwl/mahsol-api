from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class RAGAskRequest(BaseModel):
    user_id: str = Field(
        default="anonymous",
        description="User identifier. Any string works — unknown IDs start fresh history.",
    )
    question: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "farmer_001",
                "question": "What are the symptoms of early blight in tomatoes?",
                "top_k": 5,
            }
        }
    )


class SourceDocument(BaseModel):
    content: str
    page_number: Optional[int] = None
    source: str
    section_title: Optional[str] = None
    element_type: str = "text"
    relevance_score: float = Field(..., ge=0.0, le=1.0)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "content": "Early blight is caused by Alternaria solani...",
                "page_number": 12,
                "source": "tomato_knowledge.pdf",
                "section_title": "Fungal Diseases",
                "element_type": "text",
                "relevance_score": 0.92,
            }
        }
    )


class RAGAskResponse(BaseModel):
    success: bool
    answer: str
    sources: List[SourceDocument]
    tokens_used: int
    model: str
    error: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "answer": "Early blight symptoms include dark concentric rings on lower leaves...",
                "sources": [],
                "tokens_used": 312,
                "model": "gpt-4o-mini",
                "error": None,
            }
        }
    )


class RAGIngestRequest(BaseModel):
    pdf_path: Optional[str] = Field(
        default=None,
        description="Override PDF path. Defaults to PDF_PATH in .env",
    )


class RAGIngestResponse(BaseModel):
    success: bool
    chunks_ingested: int
    source: str
    errors: List[str] = []
    error: Optional[str] = None


class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: Optional[str] = None


class RAGHistoryResponse(BaseModel):
    success: bool
    user_id: str
    messages: List[ChatMessage]
    total: int
    error: Optional[str] = None


# Keep backward-compatible aliases
class RAGQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)
    filters: Optional[Dict[str, Any]] = None


class RetrievedDocument(BaseModel):
    content: str
    source: str
    score: float = Field(..., ge=0.0, le=1.0)
    metadata: Optional[Dict[str, Any]] = None


class RAGQueryResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
