import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.dependencies import get_assistant_service
from app.schemas.assistant_schema import AssistantChatRequest, AssistantChatResponse
from app.services.assistant_service import AssistantService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assistant", tags=["AI Farm Assistant"])


@router.post(
    "/chat",
    response_model=AssistantChatResponse,
    summary="AI Farm Assistant Chat",
    description=(
        "Multi-turn conversational assistant for agricultural advice. "
        "Pass conversation_history for context continuity across turns. "
        "Full LLM integration activated once LLM_API_KEY is configured."
    ),
)
async def chat(
    request: Request,
    body: AssistantChatRequest,
    assistant_service: AssistantService = Depends(get_assistant_service),
) -> JSONResponse:
    try:
        result = await assistant_service.chat(
            message=body.message,
            history=[m.model_dump() for m in body.conversation_history],
            context=body.context,
        )
    except Exception:
        logger.error("Assistant chat error", exc_info=True)
        raise HTTPException(status_code=500, detail="Assistant service unavailable")

    return JSONResponse(
        content={"success": True, "data": result, "error": None}
    )
