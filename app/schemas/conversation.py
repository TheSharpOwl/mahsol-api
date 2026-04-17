from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from app.models.message import SenderType, MessageType


class ConversationCreate(BaseModel):
    pass


class ConversationResponse(BaseModel):
    id: str
    user_id: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    sender_type: SenderType
    message_type: MessageType
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatMessageIn(BaseModel):
    message_type: MessageType = MessageType.text
    content: str


class ConversationWithMessages(BaseModel):
    id: str
    user_id: str
    created_at: datetime
    messages: List[MessageResponse] = []

    model_config = {"from_attributes": True}
