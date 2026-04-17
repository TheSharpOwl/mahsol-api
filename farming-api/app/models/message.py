import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Enum, Text, ForeignKey, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
import enum


class SenderType(str, enum.Enum):
    user = "user"
    ai = "ai"


class MessageType(str, enum.Enum):
    text = "text"
    image = "image"


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_message_type", "message_type"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sender_type: Mapped[SenderType] = mapped_column(Enum(SenderType), nullable=False)
    message_type: Mapped[MessageType] = mapped_column(Enum(MessageType), nullable=False, default=MessageType.text)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    conversation = relationship("Conversation", back_populates="messages")
