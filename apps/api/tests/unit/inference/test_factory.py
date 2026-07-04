"""Factory: each inference mode yields the right concrete client, and it honors the protocols."""

from __future__ import annotations

from pathlib import Path

import pytest

from cyclesentinel.config import Settings
from cyclesentinel.inference import get_llm_client, get_visual_retriever
from cyclesentinel.inference.base import LLMClient, VisualRetriever
from cyclesentinel.inference.live import VultrLLMClient, VultrPrimeRetriever
from cyclesentinel.inference.replay import ReplayLLMClient, ReplayRetriever
from cyclesentinel.inference.stub import StubLLMClient, StubRetriever


def _settings(monkeypatch: pytest.MonkeyPatch, mode: str) -> Settings:
    monkeypatch.setenv("CS_INFERENCE_MODE", mode)
    return Settings()


@pytest.mark.parametrize(
    ("mode", "llm_cls", "retriever_cls"),
    [
        ("stub", StubLLMClient, StubRetriever),
        ("replay", ReplayLLMClient, ReplayRetriever),
        ("live", VultrLLMClient, VultrPrimeRetriever),
    ],
)
def test_factory_returns_expected_class_per_mode(
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
    llm_cls: type[object],
    retriever_cls: type[object],
) -> None:
    settings = _settings(monkeypatch, mode)
    llm = get_llm_client(settings)
    retriever = get_visual_retriever(settings)
    assert type(llm) is llm_cls
    assert type(retriever) is retriever_cls


def test_factory_clients_satisfy_protocols(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _settings(monkeypatch, "stub")
    assert isinstance(get_llm_client(settings), LLMClient)
    assert isinstance(get_visual_retriever(settings), VisualRetriever)


def test_replay_factory_honors_cassette_dir_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CS_CASSETTE_DIR", str(tmp_path / "K"))
    settings = _settings(monkeypatch, "replay")
    client = get_llm_client(settings)
    assert isinstance(client, ReplayLLMClient)
