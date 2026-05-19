from pydantic import BaseModel
from app.schemas.conversation import MessageResponse

class ChatRequest(BaseModel):
    message_type: str = "text"
    content: str

class ChatResponse(BaseModel):
    user_message: MessageResponse
    ai_message: MessageResponse
