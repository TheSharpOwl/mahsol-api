import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db, async_session_factory
from app.models.conversation import Conversation
from app.models.message import Message, SenderType, MessageType
from app.models.user import User
from app.schemas.conversation import MessageResponse
from app.core.security import decode_token, get_current_user
from app.services.ai_service import get_chat_response

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Chat"])


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, conversation_id: str, websocket: WebSocket):
        await websocket.accept()
        if conversation_id not in self.active_connections:
            self.active_connections[conversation_id] = []
        self.active_connections[conversation_id].append(websocket)

    def disconnect(self, conversation_id: str, websocket: WebSocket):
        if conversation_id in self.active_connections:
            self.active_connections[conversation_id].remove(websocket)

    async def send_message(self, conversation_id: str, message: dict):
        if conversation_id in self.active_connections:
            for ws in self.active_connections[conversation_id]:
                try:
                    await ws.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"Failed to send WS message: {e}")


manager = ConnectionManager()


@router.websocket("/ws/chat/{conversation_id}")
async def websocket_chat(websocket: WebSocket, conversation_id: str):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001)
        return

    payload = decode_token(token)
    if not payload:
        await websocket.close(code=4001)
        return

    user_id = payload.get("sub")

    async with async_session_factory() as db:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        conversation = result.scalar_one_or_none()

    if not conversation:
        await websocket.close(code=4004)
        return

    await manager.connect(conversation_id, websocket)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
                content = data.get("content", "")
                message_type_str = data.get("message_type", "text")
                message_type = MessageType.image if message_type_str == "image" else MessageType.text
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"error": "Invalid JSON"}))
                continue

            async with async_session_factory() as db:
                user_msg = Message(
                    conversation_id=conversation_id,
                    sender_type=SenderType.user,
                    message_type=message_type,
                    content=content,
                )
                db.add(user_msg)
                await db.commit()
                await db.refresh(user_msg)

            user_msg_data = MessageResponse.model_validate(user_msg).model_dump(mode="json")
            await manager.send_message(conversation_id, {"type": "message", "data": user_msg_data})

            if message_type == MessageType.text:
                ai_reply_text = await get_chat_response(content)
            else:
                ai_reply_text = (
                    "I've received your image. Based on what I can see, this appears to show signs of "
                    "possible disease or stress in your crop. "
                    "Please share more details about when you first noticed this and the affected area size "
                    "for a more precise diagnosis."
                )

            async with async_session_factory() as db:
                ai_msg = Message(
                    conversation_id=conversation_id,
                    sender_type=SenderType.ai,
                    message_type=MessageType.text,
                    content=ai_reply_text,
                )
                db.add(ai_msg)
                await db.commit()
                await db.refresh(ai_msg)

            ai_msg_data = MessageResponse.model_validate(ai_msg).model_dump(mode="json")
            await manager.send_message(conversation_id, {"type": "message", "data": ai_msg_data})

    except WebSocketDisconnect:
        manager.disconnect(conversation_id, websocket)
        logger.info(f"WebSocket disconnected for conversation {conversation_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(conversation_id, websocket)
