"""End-to-end trajectory tests: the exact ordered event sequence + final states per demo case.

Each case runs in BOTH ``replay`` (seeded cassettes) and ``stub`` (scripted prose + corpus
retriever). The event-TYPE sequence, final states, and conditional branches are backend-independent
and asserted in both; the precise citations (page/article) are asserted only in replay, where the
recorded Prime-8B hits pin the exact page.

The R case is the invariant that proves this is an agent, not RAG: it emits ``compute`` events but
ZERO ``branch`` / ``retrieve_rule`` / ``escalate``.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest
from sqlalchemy.orm import Session

from cyclesentinel.events import AgentEvent, BriefEvent, DoneEvent
from cyclesentinel.retrieval.corpus import Corpus
from cyclesentinel.tools import ToolContext

from .conftest import build_replay_runner, build_stub_runner, prepare_case

_COMPUTE = ["compute"] * 6

EXPECTED_TYPES: dict[str, list[str]] = {
    "K": [
        "plan",
        "retrieve",
        "retrieve",
        *_COMPUTE,
        "branch",
        "retrieve_rule",
        "branch",
        "retrieve_rule",
        "action",
        "brief",
        "escalate",
        "done",
    ],
    "R": ["plan", "retrieve", "retrieve", *_COMPUTE, "action", "brief", "done"],
    "P": [
        "plan",
        "retrieve",
        "retrieve",
        *_COMPUTE,
        "branch",
        "retrieve_rule",
        "action",
        "brief",
        "escalate",
        "done",
    ],
    "M": ["plan", "retrieve", "retrieve", *_COMPUTE, "action", "brief", "escalate", "done"],
}

EXPECTED_STATES: dict[str, list[str]] = {
    "K": ["OHSS_RISK_ESCALATE", "PREMATURE_LUTEINIZATION_FLAG"],
    "R": ["ROUTINE_CONTINUE"],
    "P": ["POOR_RESPONSE_FLAG"],
    "M": ["MISSING_TIMEPOINT"],
}

EXPECTED_BRANCHES: dict[str, list[str]] = {
    "K": ["ohss", "luteinization"],
    "R": [],
    "P": ["poor_responder"],
    "M": [],
}

# (doc_id, rule_type, page, article) — replay only (cassette hits pin the exact page).
EXPECTED_CITATIONS: dict[str, list[tuple[str, str, int, str]]] = {
    "K": [("ohss_sop", "ohss", 4, "§4.2"), ("luteinization", "luteinization", 3, "§2.4")],
    "R": [("stimulation", "stimulation", 2, "§1.2")],
    "P": [("poor_responder", "poor_responder", 3, "§3.2")],
    "M": [("stimulation", "stimulation", 2, "§1.2")],
}


async def _run(
    case: str,
    mode: str,
    session: Session,
    ctx_factory: Callable[[object], ToolContext],
    corpus: Corpus,
) -> list[AgentEvent]:
    run = prepare_case(session, case)
    if mode == "replay":
        runner = build_replay_runner(case, run, ctx_factory)
    else:
        runner = build_stub_runner(case, run, ctx_factory, corpus)
    return [event async for event in runner.run(run.patient, run.result)]


@pytest.mark.parametrize("case", ["K", "R", "P", "M"])
@pytest.mark.parametrize("mode", ["replay", "stub"])
async def test_event_sequence_and_states(
    case: str,
    mode: str,
    session: Session,
    ctx_factory: Callable[[object], ToolContext],
    corpus: Corpus,
) -> None:
    events = await _run(case, mode, session, ctx_factory, corpus)

    assert [e.type for e in events] == EXPECTED_TYPES[case]

    done = events[-1]
    assert isinstance(done, DoneEvent)
    assert [str(s) for s in done.final_states] == EXPECTED_STATES[case]

    branches = [e.rule_type for e in events if e.type == "retrieve_rule"]
    assert [str(rt) for rt in branches] == EXPECTED_BRANCHES[case]

    # Step numbers are strictly increasing across every stepped event.
    steps = [e.step for e in events if hasattr(e, "step")]
    assert steps == sorted(steps)
    assert len(set(steps)) == len(steps)


def test_routine_is_the_not_rag_invariant() -> None:
    """The R sequence must contain no conditional retrieval or escalation (documentation guard)."""
    types = EXPECTED_TYPES["R"]
    assert "branch" not in types
    assert "retrieve_rule" not in types
    assert "escalate" not in types
    assert "compute" in types


@pytest.mark.parametrize("case", ["K", "R", "P", "M"])
async def test_replay_citations_resolve_to_manifest_pages(
    case: str,
    session: Session,
    ctx_factory: Callable[[object], ToolContext],
    corpus: Corpus,
) -> None:
    events = await _run(case, "replay", session, ctx_factory, corpus)
    brief_events = [e for e in events if isinstance(e, BriefEvent)]
    assert len(brief_events) == 1
    citations = brief_events[0].brief.citations
    got = [(c.doc_id, str(c.rule_type), c.page, c.article) for c in citations]
    assert got == EXPECTED_CITATIONS[case]

    # Every cited quote resolves to real page text in the corpus (hard rule 3).
    for citation in citations:
        page_text = corpus.get_page_text(citation.doc_id, citation.page)
        assert citation.quote in page_text
        assert citation.article in page_text
