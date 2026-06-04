"""
AI Farm Assistant service — scaffold for LLM + tool integration.

Future implementation:
  - System prompt built from farm context (location, crop, weather)
  - Multi-turn conversation history passed to LLM
  - Tool use: disease DB lookup, treatment recommendations, weather API
  - RAG pipeline for knowledge retrieval
  - Streaming responses via SSE
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AssistantService:
    async def chat(
        self,
        message: str,
        history: List[Dict[str, str]],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process a user message and return an AI response.

        Placeholder implementation — replace with real LLM call.
        """
        logger.info("Assistant chat", extra={"message_preview": message[:80]})

        response_text = self._placeholder_response(message, context)

        return {
            "response": response_text,
            "conversation_id": None,   # Future: UUID per session
            "sources": [],             # Future: RAG source documents
            "tool_calls": [],          # Future: executed tools list
            "model": "placeholder",    # Future: actual model ID
            "tokens_used": 0,
        }

    async def get_treatment_plan(
        self,
        disease: str,
        severity: str = "moderate",
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Return treatment recommendations for a detected disease."""
        # Future: query knowledge base + LLM synthesis
        return {
            "disease": disease,
            "severity": severity,
            "chemical_treatments": [],
            "organic_treatments": [],
            "preventive_measures": [],
            "note": "Connect knowledge base for actual recommendations.",
        }

    # ── Private ───────────────────────────────────────────────────────────────

    def _placeholder_response(
        self, message: str, context: Optional[Dict[str, Any]]
    ) -> str:
        ctx_str = ""
        if context:
            ctx_str = " | ".join(f"{k}: {v}" for k, v in context.items())
            ctx_str = f"\n[Context: {ctx_str}]"

        return (
            f"[AI Farm Assistant — placeholder]{ctx_str}\n\n"
            f"Your message: \"{message}\"\n\n"
            "This endpoint will deliver GPT-4o / Claude-powered agricultural guidance "
            "with real-time disease information, treatment plans, and farm advice. "
            "Set LLM_API_KEY in .env to activate."
        )
