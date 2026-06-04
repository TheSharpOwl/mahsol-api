"""
OpenAI gpt-4o-mini answer generator.

Prompt design rationale:
  - System prompt locks the model as a Syrian tomato farming expert.
  - "Answer ONLY using the provided context" prevents hallucination — the model
    cannot invent treatments that aren't in the knowledge base.
  - "Respond in the SAME LANGUAGE" handles bilingual Arabic/English users.
  - "Numbered steps" forces structured treatment instructions rather than prose.
  - Temperature 0.3 keeps answers deterministic and factual.
  - Context block explicitly marks chunk boundaries with [Source N] so the model
    can reason about which source contains which information.

Message order sent to OpenAI:
  [system prompt]
  [history turn 1 user] [history turn 1 assistant]
  ...
  [history turn N user] [history turn N assistant]
  [current user: CONTEXT block + QUESTION]
"""

import logging
from dataclasses import dataclass
from typing import Dict, List

from openai import AsyncOpenAI

from app.core.config import settings
from app.rag.retriever.retriever import RetrievedChunk

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
أنت مساعد زراعي خبير متخصص في زراعة الطماطم في سوريا.
You are an expert agricultural assistant specialized in tomato farming in Syria.

Your role: help farmers diagnose tomato diseases, understand treatment protocols,
and follow safe agricultural guidelines.

STRICT RULES — follow these without exception:
1. Answer ONLY using the knowledge base context provided below the question.
2. If the answer is not in the context, respond EXACTLY with:
   - English: "I don't have specific information about this in my knowledge base. Please consult a local agricultural expert or extension service."
   - Arabic: "لا تتوفر لديّ معلومات كافية حول هذا الموضوع في قاعدة المعرفة. يُرجى استشارة مرشد زراعي محلي."
3. When describing treatments or procedures, use NUMBERED STEPS (1, 2, 3...).
4. Always mention safety precautions for any chemical treatment.
5. Respond in the SAME LANGUAGE the user used to ask the question.
   If the question is in Arabic → answer in Arabic.
   If the question is in English → answer in English.
6. Cite the source: at the end of your answer write "Source: [page number or section]".
7. Be concise but complete — farmers need actionable advice, not lectures.\
"""


@dataclass
class GenerationResult:
    answer: str
    model: str
    tokens_used: int


class OpenAIGenerator:
    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = settings.OPENAI_MODEL

    async def generate(
        self,
        question: str,
        context_chunks: List[RetrievedChunk],
        history: List[Dict[str, str]],
    ) -> GenerationResult:
        """
        Build messages and call OpenAI.

        Args:
            question: current user question
            context_chunks: top-k retrieved chunks from Qdrant
            history: list of {role, content} from Redis (already trimmed to MAX_CHAT_HISTORY)
        """
        context_block = self._build_context_block(context_chunks)
        messages = self._build_messages(question, context_block, history)

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=settings.OPENAI_TEMPERATURE,
            max_tokens=settings.OPENAI_MAX_TOKENS,
        )

        answer = response.choices[0].message.content or ""
        tokens_used = response.usage.total_tokens if response.usage else 0

        logger.info(
            "OpenAI response: model=%s tokens=%d",
            response.model,
            tokens_used,
        )

        return GenerationResult(
            answer=answer.strip(),
            model=response.model,
            tokens_used=tokens_used,
        )

    # ── Private ───────────────────────────────────────────────────────────────

    def _build_context_block(self, chunks: List[RetrievedChunk]) -> str:
        if not chunks:
            return "No relevant context found in the knowledge base."

        parts = []
        for i, chunk in enumerate(chunks, start=1):
            meta = []
            if chunk.page_number:
                meta.append(f"page {chunk.page_number}")
            if chunk.section_title:
                meta.append(f"section: {chunk.section_title}")
            if chunk.element_type == "table":
                meta.append("table")

            header = f"[Source {i}]" + (f" ({', '.join(meta)})" if meta else "")
            parts.append(f"{header}\n{chunk.content}")

        return "\n\n---\n\n".join(parts)

    def _build_messages(
        self,
        question: str,
        context_block: str,
        history: List[Dict[str, str]],
    ) -> List[Dict[str, str]]:
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": _SYSTEM_PROMPT}
        ]

        # Inject conversation history (already in OpenAI format from get_history_for_llm)
        messages.extend(history)

        # Inject context + current question as the user turn
        user_content = (
            f"KNOWLEDGE BASE CONTEXT:\n"
            f"{'=' * 60}\n"
            f"{context_block}\n"
            f"{'=' * 60}\n\n"
            f"QUESTION:\n{question}"
        )
        messages.append({"role": "user", "content": user_content})

        return messages
