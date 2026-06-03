from pydantic import BaseModel
from typing import Optional
from app.schemas.conversation import MessageResponse

class ChatRequest(BaseModel):
    content: Optional[str] = None
    message_type: str = "text"  # "text" or "image"
    file_id: Optional[str] = None

class ChatResponse(BaseModel):
    user_message: MessageResponse
    ai_message: MessageResponse