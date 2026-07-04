"""Replay-mode clients: deterministic playback from recorded cassettes (CI/tests).

Both clients are read-only. A cassette *miss* raises :class:`CassetteMissError` loudly and never
falls back to the network — replay must be hermetic. Cassettes are recorded once against the live
path (or hand-authored by the Tools/Data lanes) using the identical request-keying in
:mod:`cyclesentinel.inference.cassette`, so the key computed here matches the key recorded there.
"""

from __future__ import annotations

from cyclesentinel.enums import RuleType
from cyclesentinel.inference.base import ChatMessage, ChatResponse, ToolSchema
from cyclesentinel.inference.cassette import Cassette, llm_request_key, retriever_request_key
from cyclesentinel.schemas import RetrievalHit


class CassetteMissError(RuntimeError):
    """Raised when replay has no recorded response for a request (never a network fallback)."""


class ReplayLLMClient:
    """Serves recorded :class:`ChatResponse` objects from an ``llm`` cassette directory."""

    def __init__(self, cassette: Cassette, *, model: str = "") -> None:
        self._cassette = cassette
        self._model = model

    async def chat(
        self, messages: list[ChatMessage], tools: list[ToolSchema] | None = None
    ) -> ChatResponse:
        """Return the recorded response for this request, or raise :class:`CassetteMissError`."""
        key = llm_request_key(messages, tools, self._model)
        raw = self._cassette.load(key)
        if raw is None:
            raise CassetteMissError(
                f"No LLM cassette for key {key} under {self._cassette.root} "
                "(replay never calls the network — record this request first)."
            )
        return ChatResponse.model_validate(raw)


class ReplayRetriever:
    """Serves recorded ``list[RetrievalHit]`` from a ``retriever`` cassette directory."""

    def __init__(self, cassette: Cassette, *, model: str = "") -> None:
        self._cassette = cassette
        self._model = model

    async def retrieve(self, query: str, rule_type: RuleType, top_k: int) -> list[RetrievalHit]:
        """Return the recorded hits for this query, truncated to ``top_k``, or raise on a miss."""
        key = retriever_request_key(query, rule_type, top_k, self._model)
        raw = self._cassette.load(key)
        if raw is None:
            raise CassetteMissError(
                f"No retriever cassette for key {key} under {self._cassette.root} "
                "(replay never calls the network — record this request first)."
            )
        if not isinstance(raw, list):
            raise CassetteMissError(
                f"Malformed retriever cassette {key} under {self._cassette.root}: "
                "expected a JSON array of RetrievalHit."
            )
        return [RetrievalHit.model_validate(hit) for hit in raw][:top_k]
