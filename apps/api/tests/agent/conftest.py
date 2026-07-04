"""Fixtures for the agent-loop tests: seeded db, wired ToolContext, and both inference backends.

Every case runs in two modes — ``replay`` (the seeded cassettes, through the real
``get_llm_client`` / ``get_visual_retriever`` factories) and ``stub`` (the same authored LLM prose
plus a corpus-backed retriever) — so the asserted event sequence is backend-independent.

The ``thresholds`` payload is the ``Thresholds`` TypedDict the calculators consume; its numbers are
tuned so the deterministic signals trip exactly as ``data/synthetic/manifest.json`` expects (OHSS +
luteinization for K, nothing for R, poor-response for P, a monitoring gap for M).
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from cyclesentinel.agent import AgentRunner
from cyclesentinel.calculators import Thresholds
from cyclesentinel.config import get_settings
from cyclesentinel.db import repo
from cyclesentinel.db.seed import seed_demo
from cyclesentinel.db.session import make_engine, make_session_factory
from cyclesentinel.enums import RuleType
from cyclesentinel.inference import get_llm_client, get_visual_retriever
from cyclesentinel.inference.base import ChatResponse, Clock, IdFactory
from cyclesentinel.inference.stub import StubLLMClient
from cyclesentinel.retrieval.corpus import Corpus, load_corpus
from cyclesentinel.schemas import HormoneResult, Patient, RetrievalHit
from cyclesentinel.tools import ToolContext, load_dose_rules

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SYNTHETIC = _REPO_ROOT / "data" / "synthetic"
_CASSETTES = _REPO_ROOT / "apps" / "api" / "tests" / "cassettes"
_BASE = datetime(2026, 7, 1, 8, 0, tzinfo=UTC)

# Manifest ground truth the trajectory tests assert against (patient/result ids per case).
CASE_IDS: dict[str, tuple[str, str]] = {
    "K": ("pat-K", "res-K-d8"),
    "R": ("pat-R", "res-R-d8"),
    "P": ("pat-P", "res-P-d8"),
    "M": ("pat-M", "res-M-d8"),
}


class CorpusRetriever:
    """A deterministic, offline retriever backed by the synthetic corpus (stub-mode stand-in).

    Returns the non-cover pages for a ``rule_type`` as scored hits whose ``text``/``article`` come
    straight from the corpus, so the grounding guard is exercised for real without cassettes.
    """

    def __init__(self, corpus: Corpus) -> None:
        self._corpus = corpus

    async def retrieve(self, query: str, rule_type: RuleType, top_k: int) -> list[RetrievalHit]:
        pages = [p for p in self._corpus.filter_by(rule_type) if p.article.lower() != "cover"]
        hits = [
            RetrievalHit(
                doc_id=page.doc_id,
                rule_type=rule_type,
                page=page.page,
                score=round(0.9 - 0.01 * index, 3),
                text=page.text,
                article=page.article,
            )
            for index, page in enumerate(pages)
        ]
        return hits[:top_k]


@dataclass(frozen=True)
class RunCase:
    """One prepared run: the patient, the triggering result, and its live run id."""

    case: str
    patient: Patient
    result: HormoneResult
    run_id: str


@pytest.fixture
def session() -> Iterator[Session]:
    """A fresh in-memory SQLite session seeded with all four synthetic demo cases."""
    factory = make_session_factory(make_engine("sqlite+pysqlite:///:memory:"))
    db = factory()
    seed_demo(db, _SYNTHETIC)
    db.flush()
    try:
        yield db
        db.commit()
    finally:
        db.close()


@pytest.fixture
def thresholds() -> Thresholds:
    """Calculator thresholds tuned to the manifest trip pattern (TypedDict shape)."""
    return {
        "ohss": {
            "e2_high": 3000.0,
            "rate_pct_per_day_high": 50.0,
            "mature_follicle_count_high": 18,
            "pcos_threshold_multiplier": 0.9,
        },
        "luteinization": {
            "progesterone_by_cycle_day": [
                {"max_cycle_day": 6, "threshold": 1.0},
                {"max_cycle_day": 8, "threshold": 1.5},
                {"max_cycle_day": 10, "threshold": 1.75},
            ],
            "default_threshold": 2.0,
        },
        "poor_responder": {
            "flat_rate_pct_per_day": 70.0,
            "min_e2_on_trajectory": 500.0,
        },
    }


@pytest.fixture
def corpus() -> Corpus:
    """The synthetic protocol/SOP corpus (grounds citations to real pages)."""
    return load_corpus(_SYNTHETIC / "corpus")


@pytest.fixture
def ctx_factory(
    session: Session, thresholds: Thresholds, corpus: Corpus
) -> Callable[[object], ToolContext]:
    """Build a ToolContext bound to the seeded session, given a retriever."""

    dose_table = load_dose_rules(_SYNTHETIC / "dose_tables.json")

    def build(retriever: object) -> ToolContext:
        return ToolContext(
            session=session,
            retriever=retriever,  # type: ignore[arg-type]  # VisualRetriever-shaped duck type
            thresholds=thresholds,
            dose_table=dose_table,
            corpus=corpus,
            ids=IdFactory("id"),
            clock=Clock(_BASE),
        )

    return build


def _authored_response(case: str, turn: str) -> ChatResponse:
    """Load one hand-authored LLM turn (``01_plan`` / ``02_brief``) as a ChatResponse."""
    raw = json.loads((_CASSETTES / case / "llm" / f"{turn}.json").read_text(encoding="utf-8"))
    return ChatResponse.model_validate(raw)


def prepare_case(session: Session, case: str) -> RunCase:
    """Load the case patient + result and open a live run for it."""
    patient_id, result_id = CASE_IDS[case]
    patient = repo.get_patient(session, patient_id)
    result = repo.get_result(session, result_id)
    assert patient is not None
    assert result is not None
    run = repo.create_run(session, patient_id, result_id)
    return RunCase(case=case, patient=patient, result=result, run_id=run.run_id)


def build_replay_runner(
    case: str, run: RunCase, ctx_factory: Callable[[object], ToolContext]
) -> AgentRunner:
    """An AgentRunner wired to the seeded cassettes for ``case`` (real replay factories)."""
    os.environ["CS_CASSETTE_DIR"] = str(_CASSETTES / case)
    settings = get_settings()
    retriever = get_visual_retriever(settings)
    ctx = ctx_factory(retriever)
    llm = get_llm_client(settings)
    return AgentRunner(llm=llm, ctx=ctx, run_id=run.run_id)


def build_stub_runner(
    case: str, run: RunCase, ctx_factory: Callable[[object], ToolContext], corpus: Corpus
) -> AgentRunner:
    """An AgentRunner using scripted stub LLM turns + a corpus-backed retriever (no cassettes)."""
    llm = StubLLMClient([_authored_response(case, "01_plan"), _authored_response(case, "02_brief")])
    ctx = ctx_factory(CorpusRetriever(corpus))
    return AgentRunner(llm=llm, ctx=ctx, run_id=run.run_id)
