"""Stub-mode clients: canned, in-code outputs for fast unit tests (no files, no network).

Use these to unit-test callers that only need *some* deterministic response.
:class:`StubLLMClient` can be scripted with a queue of responses (popped in order) for multi-turn
tool loops; once the queue drains it returns a fixed default. :class:`StubRetriever` returns one
synthetic hit per requested ``rule_type`` (truncated to ``top_k``).
"""

from __future__ import annotations

from cyclesentinel.enums import RuleType
from cyclesentinel.inference.base import ChatMessage, ChatResponse, ToolSchema
from cyclesentinel.schemas import RetrievalHit

_DEFAULT_CONTENT = "stub: no scripted response"


class StubLLMClient:
    """Returns scripted :class:`ChatResponse` objects in order, then a fixed default."""

    def __init__(self, responses: list[ChatResponse] | None = None) -> None:
        self._responses = list(responses) if responses else []
        self.calls = 0

    async def chat(
        self, messages: list[ChatMessage], tools: list[ToolSchema] | None = None
    ) -> ChatResponse:
        """Pop and return the next scripted response, or a canned default if the queue is empty."""
        self.calls += 1
        if self._responses:
            return self._responses.pop(0)
        return ChatResponse(content=_DEFAULT_CONTENT, tool_calls=[])


class StubRetriever:
    """Returns a single synthetic :class:`RetrievalHit` for the requested ``rule_type``."""

    async def retrieve(self, query: str, rule_type: RuleType, top_k: int) -> list[RetrievalHit]:
        """Return one canned hit tagged with ``rule_type`` (respecting a ``top_k`` of 0)."""
        hit = RetrievalHit(
            doc_id=f"stub-{rule_type}",
            rule_type=rule_type,
            page=1,
            score=0.99,
            text=f"stub page text for {rule_type}: {query}",
            article="§1",
        )
        return [hit][:top_k]
