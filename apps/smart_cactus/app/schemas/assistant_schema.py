from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    role: MessageRole
    content: str = Field(..., min_length=1)


class AssistantChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4096)
    conversation_history: List[ChatMessage] = Field(
        default_factory=list,
        description="Prior turns for multi-turn context",
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional farm context — location, crop type, weather, etc.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "My tomato plants have dark spots on the leaves, what disease could this be?",
                "conversation_history": [],
                "context": {
                    "location": "Cairo, Egypt",
                    "crop": "tomato",
                    "weather": "humid",
                },
            }
        }
    )


class AssistantChatResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
