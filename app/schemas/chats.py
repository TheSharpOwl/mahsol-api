from pydantic import BaseModel
from typing import Optional, List
from app.schemas.conversation import MessageResponse
from app.schemas.product import ProductResponse

class ChatRequest(BaseModel):
    content: str
    message_type: Optional[str] = "text"

class ChatResponse(BaseModel):
    user_message: MessageResponse
    ai_message: MessageResponse
    action: Optional[str] = None
    products: List[ProductResponse] = []

    class Config:
        from_attributes = True
