"""The grounding guard and the ambiguous fail-safe (bad model output never resolves to normal)."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from sqlalchemy.orm import Session

from cyclesentinel.agent import (
    AgentAmbiguousError,
    AgentRunner,
    RetryPolicy,
    draft_brief,
    is_grounded,
)
from cyclesentinel.enums import DecisionState, EscalationLevel, RuleType
from cyclesentinel.events import DoneEvent, ErrorEvent
from cyclesentinel.inference.base import ChatResponse
from cyclesentinel.inference.stub import StubLLMClient, StubRetriever
from cyclesentinel.retrieval.corpus import Corpus
from cyclesentinel.schemas import Citation, RetrievalHit
from cyclesentinel.tools import ToolContext

from .conftest import CorpusRetriever, prepare_case

_HIT = RetrievalHit(
    doc_id="ohss_sop",
    rule_type=RuleType.OHSS,
    page=4,
    score=0.9,
    text="§4.2 Escalation and management\nWithhold the standard trigger and escalate.",
    article="§4.2",
)


def test_is_grounded_true_when_quote_and_article_on_page() -> None:
    citation = Citation(
        doc_id="ohss_sop",
        rule_type=RuleType.OHSS,
        page=4,
        article="§4.2",
        quote="§4.2 Escalation and management",
    )
    assert is_grounded([citation], [_HIT], None) is True


def test_is_grounded_false_when_quote_absent() -> None:
    citation = Citation(
        doc_id="ohss_sop",
        rule_type=RuleType.OHSS,
        page=4,
        article="§4.2",
        quote="a line that is not on the page",
    )
    assert is_grounded([citation], [_HIT], None) is False


def test_is_grounded_false_when_no_page_source() -> None:
    citation = Citation(
        doc_id="ghost",
        rule_type=RuleType.OHSS,
        page=99,
        article="§9.9",
        quote="anything",
    )
    assert is_grounded([citation], [], None) is False


async def test_draft_brief_rejects_ungrounded_citation(
    session: Session,
    ctx_factory: Callable[[object], ToolContext],
    corpus: Corpus,
) -> None:
    run = prepare_case(session, "K")
    ctx = ctx_factory(CorpusRetriever(corpus))
    llm = StubLLMClient(
        [ChatResponse(content='{"interpretation": "ok", "recommended_action": "do"}')]
    )
    ungrounded = Citation(
        doc_id="ohss_sop",
        rule_type=RuleType.OHSS,
        page=4,
        article="§9.9",  # not on page 4
        quote="a fabricated quote",
    )
    with pytest.raises(AgentAmbiguousError):
        await draft_brief(
            llm,
            ctx,
            patient=run.patient,
            result=run.result,
            results=[run.result],
            run_id=run.run_id,
            states=[DecisionState.OHSS_RISK_ESCALATE],
            citations=[ungrounded],
            escalation_level=EscalationLevel.URGENT,
            hits=[],
        )


async def test_bad_plan_output_fails_safe_to_ambiguous(
    session: Session,
    ctx_factory: Callable[[object], ToolContext],
) -> None:
    run = prepare_case(session, "R")
    ctx = ctx_factory(StubRetriever())
    llm = StubLLMClient([ChatResponse(content="not valid json at all")])
    runner = AgentRunner(llm=llm, ctx=ctx, run_id=run.run_id, retry_policy=RetryPolicy(retries=0))
    events = [event async for event in runner.run(run.patient, run.result)]

    assert any(isinstance(e, ErrorEvent) for e in events)
    done = events[-1]
    assert isinstance(done, DoneEvent)
    assert done.final_states == [DecisionState.AMBIGUOUS_REQUIRES_REVIEW]
