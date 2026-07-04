"""Mode-agnostic inference seam: protocols, wire DTOs, and determinism helpers.

The agent loop depends only on the :class:`LLMClient` and :class:`VisualRetriever` *protocols*
defined here — it never learns whether it is talking to the live Vultr stack, a replay cassette, or
an in-code stub. The concrete clients live in the ``live`` / ``replay`` / ``stub`` modules; the
``get_llm_client`` / ``get_visual_retriever`` factories pick one from ``settings.inference_mode``.

DTOs mirror the OpenAI-compatible chat-completions wire shape (Vultr speaks it), kept deliberately
small. :class:`IdFactory` and :class:`Clock` give deterministic ids/timestamps and are injected into
the tool layer (via ``ToolContext``) so a run is byte-reproducible under replay.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from cyclesentinel.enums import RuleType
from cyclesentinel.schemas import RetrievalHit

Role = Literal["system", "user", "assistant", "tool"]


class ToolCall(BaseModel):
    """A single tool/function call the model asked for (arguments already parsed to a dict)."""

    id: str
    name: str
    arguments: dict[str, object] = Field(default_factory=dict)

    def to_wire(self) -> dict[str, object]:
        """Render back to the OpenAI-compatible ``assistant`` tool-call shape."""
        return {
            "id": self.id,
            "type": "function",
            "function": {
                "name": self.name,
                "arguments": json.dumps(self.arguments, sort_keys=True),
            },
        }


class ChatMessage(BaseModel):
    """One message in a chat-completions conversation.

    ``tool_call_id``/``name`` are set on ``role="tool"`` result messages; ``tool_calls`` is set on
    an ``role="assistant"`` message that requested tools (so the loop can replay that turn).
    """

    role: Role
    content: str | None = None
    tool_call_id: str | None = None
    name: str | None = None
    tool_calls: list[ToolCall] | None = None

    def to_wire(self) -> dict[str, object]:
        """Serialize to the OpenAI-compatible ``messages[]`` element, omitting unset optionals."""
        wire: dict[str, object] = {"role": self.role}
        if self.content is not None:
            wire["content"] = self.content
        if self.name is not None:
            wire["name"] = self.name
        if self.tool_call_id is not None:
            wire["tool_call_id"] = self.tool_call_id
        if self.tool_calls:
            wire["tool_calls"] = [tc.to_wire() for tc in self.tool_calls]
        return wire


class ToolSchema(BaseModel):
    """A tool the model may call — ``parameters`` is a JSON-Schema object for its arguments."""

    name: str
    description: str
    parameters: dict[str, object] = Field(default_factory=dict)

    def to_wire(self) -> dict[str, object]:
        """Render to the OpenAI-compatible ``tools[]`` element (``{"type":"function", ...}``)."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ChatResponse(BaseModel):
    """A single assistant turn: prose ``content`` and/or a list of requested ``tool_calls``."""

    content: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)


@runtime_checkable
class LLMClient(Protocol):
    """A text LLM (Kimi K2 on the live path) that plans, interprets, and requests tool calls."""

    async def chat(
        self, messages: list[ChatMessage], tools: list[ToolSchema] | None = None
    ) -> ChatResponse:
        """Run one chat-completions turn at temperature 0 and return the assistant response."""
        ...


@runtime_checkable
class VisualRetriever(Protocol):
    """The visual document retriever (Vultron Prime-8B) behind ``retrieve_protocol_rule``."""

    async def retrieve(self, query: str, rule_type: RuleType, top_k: int) -> list[RetrievalHit]:
        """Return the top-``k`` protocol/SOP pages for ``query``, filtered to ``rule_type``."""
        ...


class IdFactory:
    """Seeded, monotonic id generator for deterministic runs (``call-0001``, ``call-0002``, …).

    ``namespace`` (default empty — unchanged output) prepends a per-run token so ids minted across
    separate runs sharing one database stay unique (e.g. persisted brief ids). The counter is still
    reset-per-run, so within a run the sequence is deterministic and replay-stable.
    """

    def __init__(
        self, prefix: str = "id", *, start: int = 1, width: int = 4, namespace: str = ""
    ) -> None:
        self._prefix = prefix
        self._start = start
        self._counter = start
        self._width = width
        self._namespace = namespace

    def next(self, prefix: str | None = None) -> str:
        """Return the next id, optionally overriding the default prefix for this one id."""
        value = self._counter
        self._counter += 1
        return f"{self._namespace}{prefix or self._prefix}-{value:0{self._width}d}"

    def reset(self) -> None:
        """Rewind the counter to its seed (for a fresh, reproducible run)."""
        self._counter = self._start


class Clock:
    """Deterministic clock: starts at a fixed base and advances only when explicitly ticked."""

    def __init__(self, base: datetime, *, step: timedelta = timedelta(seconds=1)) -> None:
        self._base = base
        self._current = base
        self._step = step

    def now(self) -> datetime:
        """Return the current (frozen) time without advancing it."""
        return self._current

    def tick(self, delta: timedelta | None = None) -> datetime:
        """Advance the clock by ``delta`` (or the default step) and return the new time."""
        self._current += delta if delta is not None else self._step
        return self._current

    def reset(self) -> None:
        """Rewind to the base time (for a fresh, reproducible run)."""
        self._current = self._base
