"""Vultr inference clients (LLM + retriever) and the live/replay/stub mode switch.

The rest of the app depends only on the :class:`LLMClient` / :class:`VisualRetriever` protocols and
gets a concrete client from :func:`get_llm_client` / :func:`get_visual_retriever`, keyed on
``settings.inference_mode``. Replay reads cassettes rooted at ``CS_CASSETTE_DIR`` (default
``apps/api/tests/cassettes``); point it at ``…/cassettes/<CASE>`` to serve a specific demo case.
"""

from __future__ import annotations

import os
from pathlib import Path

from cyclesentinel.config import Settings
from cyclesentinel.inference.base import (
    ChatMessage,
    ChatResponse,
    Clock,
    IdFactory,
    LLMClient,
    Role,
    ToolCall,
    ToolSchema,
    VisualRetriever,
)
from cyclesentinel.inference.cassette import (
    Cassette,
    cassette_key,
    llm_request_key,
    retriever_request_key,
)
from cyclesentinel.inference.live import VultrLLMClient, VultrPrimeRetriever
from cyclesentinel.inference.replay import CassetteMissError, ReplayLLMClient, ReplayRetriever
from cyclesentinel.inference.stub import StubLLMClient, StubRetriever

__all__ = [
    "Cassette",
    "CassetteMissError",
    "ChatMessage",
    "ChatResponse",
    "Clock",
    "IdFactory",
    "LLMClient",
    "ReplayLLMClient",
    "ReplayRetriever",
    "Role",
    "StubLLMClient",
    "StubRetriever",
    "ToolCall",
    "ToolSchema",
    "VisualRetriever",
    "VultrLLMClient",
    "VultrPrimeRetriever",
    "cassette_key",
    "get_llm_client",
    "get_visual_retriever",
    "llm_request_key",
    "retriever_request_key",
]

# Repo layout: .../cyclesentinel/inference/__init__.py → parents[3] == apps/api.
_DEFAULT_CASSETTE_DIR = Path(__file__).resolve().parents[3] / "tests" / "cassettes"


def _cassette_dir() -> Path:
    """Root cassette directory: ``CS_CASSETTE_DIR`` if set, else the default under ``apps/api``."""
    override = os.environ.get("CS_CASSETTE_DIR")
    return Path(override) if override else _DEFAULT_CASSETTE_DIR


def _replay_cassette(kind: str) -> Cassette:
    """Build the replay cassette for ``kind`` (``"llm"`` | ``"retriever"``).

    With ``CS_CASSETTE_DIR`` pinned to one case, serve only ``<dir>/<kind>``. Otherwise search every
    per-case dir ``<base>/*/<kind>`` (plus a flat ``<base>/<kind>``) so one running server resolves
    any demo patient's cassette — keys are unique content hashes, so there is no cross-case clash.
    """
    if os.environ.get("CS_CASSETTE_DIR"):
        return Cassette(_cassette_dir() / kind)
    base = _DEFAULT_CASSETTE_DIR
    per_case = tuple(sorted(p for p in base.glob(f"*/{kind}") if p.is_dir()))
    return Cassette(base / kind, extra_roots=per_case)


def get_llm_client(settings: Settings) -> LLMClient:
    """Return the LLM client for ``settings.inference_mode`` (live | replay | stub)."""
    mode = settings.inference_mode
    if mode == "live":
        return VultrLLMClient(settings)
    if mode == "replay":
        return ReplayLLMClient(_replay_cassette("llm"), model=settings.cs_llm_model)
    if mode == "stub":
        return StubLLMClient()
    raise ValueError(f"Unknown inference_mode: {mode!r}")


def get_visual_retriever(settings: Settings) -> VisualRetriever:
    """Return the visual retriever for ``settings.inference_mode`` (live | replay | stub)."""
    mode = settings.inference_mode
    if mode == "live":
        return VultrPrimeRetriever(settings)
    if mode == "replay":
        return ReplayRetriever(_replay_cassette("retriever"), model=settings.cs_retriever_model)
    if mode == "stub":
        return StubRetriever()
    raise ValueError(f"Unknown inference_mode: {mode!r}")
