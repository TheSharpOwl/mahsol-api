"""
Redis-backed per-user chat history.

Key design decisions:
  - Key pattern: mahsoul:chat:{user_id}  (Redis list, right-to-right order)
  - Each entry: JSON-serialized {role, content, timestamp}
  - Capacity: capped to MAX_CHAT_HISTORY via LTRIM after each RPUSH
  - TTL: sliding 7-day window reset on every write (so active users never expire)
  - New users: get_history() on an unknown user_id returns [] — no registration needed

How history improves RAG quality:
  - The LLM sees prior Q&A turns, so follow-up questions ("what about dosage?")
    are correctly disambiguated without repeating context.
  - Contradictions are avoided because the model remembers its own previous answers.
  - Multi-step conversations ("first diagnose, then treat") stay coherent.
"""

import json
import logging
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, List, Optional

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

_KEY_PREFIX = "mahsoul:chat:"


class RedisChatMemory:
    _instance: Optional["RedisChatMemory"] = None
    _lock: Lock = Lock()

    def __init__(self, client: aioredis.Redis) -> None:
        self._redis = client

    # ── Singleton (async — must be awaited once at startup) ───────────────────

    @classmethod
    async def get_instance(cls) -> "RedisChatMemory":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    client = aioredis.from_url(
                        settings.REDIS_URL,
                        encoding="utf-8",
                        decode_responses=True,
                    )
                    await client.ping()
                    cls._instance = cls(client)
                    logger.info("Redis chat memory connected: %s", settings.REDIS_URL)
        return cls._instance

    # ── Public API ────────────────────────────────────────────────────────────

    async def add_message(self, user_id: str, role: str, content: str) -> None:
        """Append one message and trim to MAX_CHAT_HISTORY, then refresh TTL."""
        key = _KEY_PREFIX + user_id
        entry = json.dumps(
            {
                "role": role,
                "content": content,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            ensure_ascii=False,
        )
        pipe = self._redis.pipeline()
        pipe.rpush(key, entry)
        pipe.ltrim(key, -settings.MAX_CHAT_HISTORY, -1)  # keep last N
        pipe.expire(key, settings.CHAT_HISTORY_TTL)
        await pipe.execute()

    async def get_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Return all stored messages for user_id. Returns [] for unknown users."""
        key = _KEY_PREFIX + user_id
        raw_entries = await self._redis.lrange(key, 0, -1)
        messages = []
        for raw in raw_entries:
            try:
                messages.append(json.loads(raw))
            except json.JSONDecodeError:
                logger.warning("Skipping malformed chat history entry for user %s", user_id)
        return messages

    async def clear_history(self, user_id: str) -> None:
        """Delete all history for a user."""
        key = _KEY_PREFIX + user_id
        await self._redis.delete(key)
        logger.info("Cleared chat history for user '%s'", user_id)

    async def get_history_for_llm(self, user_id: str) -> List[Dict[str, str]]:
        """Return history in OpenAI message format: [{role, content}, ...]."""
        history = await self.get_history(user_id)
        return [{"role": m["role"], "content": m["content"]} for m in history]
