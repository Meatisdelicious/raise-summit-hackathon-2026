"""The brief turn: ask the LLM for the interpretation/action prose, then assemble a grounded brief.

The LLM writes only prose (``{"interpretation", "recommended_action"}``); the decision states,
citations, and escalation level are supplied by the deterministic pipeline. The **grounding guard**
enforces hard rule 3: every citation's quote and article must actually appear on a retrieved page
(or the corpus page it was drawn from). On malformed prose or a failed guard the turn retries once,
then raises :class:`AgentAmbiguousError` -> ``AMBIGUOUS_REQUIRES_REVIEW``.
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from cyclesentinel.agent.limits import AgentAmbiguousError, RetryPolicy
from cyclesentinel.agent.prompts import brief_messages, run_query
from cyclesentinel.enums import DecisionState, EscalationLevel
from cyclesentinel.inference.base import ChatResponse, LLMClient
from cyclesentinel.retrieval.corpus import Corpus
from cyclesentinel.schemas import Citation, HormoneResult, MonitoringBrief, Patient, RetrievalHit
from cyclesentinel.tools import ToolContext, get_tool


def _parse_prose(resp: ChatResponse) -> tuple[str, str] | None:
    """Extract ``(interpretation, recommended_action)`` from the LLM response, or ``None``."""
    content = resp.content
    if not content:
        return None
    try:
        data: object = json.loads(content)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    interpretation = data.get("interpretation")
    action = data.get("recommended_action")
    if not isinstance(interpretation, str) or not isinstance(action, str):
        return None
    if not interpretation.strip() or not action.strip():
        return None
    return interpretation, action


def _page_text(
    citation: Citation, hits: Sequence[RetrievalHit], corpus: Corpus | None
) -> str | None:
    """Resolve the page text a citation should ground against (a retrieved hit or corpus page)."""
    for hit in hits:
        if hit.doc_id == citation.doc_id and hit.page == citation.page:
            return hit.text
    if corpus is not None:
        try:
            return corpus.get_page_text(citation.doc_id, citation.page)
        except KeyError:
            return None
    return None


def is_grounded(
    citations: Sequence[Citation], hits: Sequence[RetrievalHit], corpus: Corpus | None
) -> bool:
    """True iff each citation's quote and article appear in its page text (hard rule 3)."""
    for citation in citations:
        text = _page_text(citation, hits, corpus)
        if text is None:
            return False
        if citation.quote not in text:
            return False
        if citation.article and citation.article not in text:
            return False
    return True


async def draft_brief(
    llm: LLMClient,
    ctx: ToolContext,
    *,
    patient: Patient,
    result: HormoneResult,
    results: Sequence[HormoneResult],
    run_id: str,
    states: Sequence[DecisionState],
    citations: Sequence[Citation],
    escalation_level: EscalationLevel,
    hits: Sequence[RetrievalHit],
    policy: RetryPolicy | None = None,
) -> MonitoringBrief:
    """Draft the cited brief, retrying once on bad prose / failed grounding then AMBIGUOUS."""
    policy = policy or RetryPolicy()
    messages = brief_messages(run_query(patient, results))
    spec = get_tool("create_monitoring_brief")
    for _ in range(policy.attempts):
        prose = _parse_prose(await llm.chat(messages))
        if prose is None:
            continue
        if not is_grounded(citations, hits, ctx.corpus):
            continue
        interpretation, action = prose
        brief = await spec.invoke(
            ctx,
            {
                "patient_id": patient.id,
                "result_id": result.id,
                "run_id": run_id,
                "states": list(states),
                "interpretation": interpretation,
                "recommended_action": action,
                "citations": list(citations),
                "escalation_level": escalation_level,
            },
        )
        if not isinstance(brief, MonitoringBrief):  # pragma: no cover - spec result is typed
            raise AgentAmbiguousError("brief: create_monitoring_brief returned an unexpected type")
        return brief
    raise AgentAmbiguousError("brief: model prose was invalid or ungrounded")
