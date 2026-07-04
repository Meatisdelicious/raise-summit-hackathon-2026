"""The agent orchestration loop — emits the ``AgentEvent`` trace in ``docs/doc.md`` §2 order.

:class:`AgentRunner` drives one run: plan -> retrieve(patient_context) -> retrieve(trajectory) ->
compute(signals) -> [branch -> retrieve_rule]* -> action -> brief -> escalate -> done. The
conditional ``branch``/``retrieve_rule`` pairs are reached *only* through :func:`branches_for` on
the computed signals (the "not RAG" core) — the routine case emits none. The LLM plans and writes
prose; the deterministic calculators + rules decide the states and the escalation flag.

The runner is inference-mode agnostic: it is handed an :class:`LLMClient` and a :class:`ToolContext`
(which already carries the visual retriever, db session, cited thresholds/dose table, corpus, and
deterministic id/clock). It never learns whether those are live, replay, or stub.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel
from sqlalchemy.orm import Session

from cyclesentinel.agent.branch import branches_for
from cyclesentinel.agent.brief import draft_brief
from cyclesentinel.agent.limits import (
    AgentAmbiguousError,
    RetryPolicy,
    StepBudget,
    StepBudgetError,
)
from cyclesentinel.agent.planner import make_plan
from cyclesentinel.agent.prompts import run_query
from cyclesentinel.agent.state import (
    DEFAULT_MAX_GAP_DAYS,
    compute_monitoring_gap,
    decide_states,
    escalation_for,
)
from cyclesentinel.calculators import compute_response_curve, load_thresholds
from cyclesentinel.config import Settings
from cyclesentinel.db import repo
from cyclesentinel.enums import DecisionState, EscalationLevel, RuleType
from cyclesentinel.events import (
    ActionEvent,
    AgentEvent,
    BranchEvent,
    BriefEvent,
    ComputeEvent,
    DoneEvent,
    ErrorEvent,
    EscalateEvent,
    PlanEvent,
    RetrieveEvent,
    RetrieveRuleEvent,
)
from cyclesentinel.inference.base import Clock, IdFactory, LLMClient, VisualRetriever
from cyclesentinel.retrieval.corpus import Corpus, load_corpus
from cyclesentinel.schemas import (
    Citation,
    ComputedSignal,
    HormoneResult,
    Patient,
    RetrievalHit,
)
from cyclesentinel.tools import ToolContext, ToolError, ToolSpec, get_tool, load_dose_rules
from cyclesentinel.tools.brief_tools import EscalationResult
from cyclesentinel.tools.context_tools import TrajectoryResult
from cyclesentinel.tools.dose_tool import DoseAdjustmentResult
from cyclesentinel.tools.retrieval_tool import RuleRetrievalResult

_RETRIEVAL_TOP_K = 2  # must match scripts/record_cassettes.py (cassette keys depend on it).

_BRANCH_LABEL: Mapping[RuleType, str] = {
    RuleType.OHSS: "OHSS composite tier tripped",
    RuleType.LUTEINIZATION: "progesterone elevated for cycle day",
    RuleType.POOR_RESPONDER: "E2 flat versus the expected curve",
}
_BRANCH_SIGNAL: Mapping[RuleType, str] = {
    RuleType.OHSS: "ohss_composite",
    RuleType.LUTEINIZATION: "progesterone_for_day",
    RuleType.POOR_RESPONDER: "response_curve",
}


async def _invoke[T: BaseModel](
    spec: ToolSpec, ctx: ToolContext, args: Mapping[str, object], expected: type[T]
) -> T:
    """Invoke ``spec`` and narrow its ``BaseModel`` result to the expected concrete type."""
    result = await spec.invoke(ctx, args)
    if not isinstance(result, expected):  # pragma: no cover - specs return their declared type
        raise ToolError(
            f"{spec.name} returned {type(result).__name__}, expected {expected.__name__}"
        )
    return result


def _first_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return text.strip()


def _branch_reason(rule_type: RuleType, signals: Sequence[ComputedSignal]) -> str:
    name = _BRANCH_SIGNAL[rule_type]
    detail = next((s.detail for s in signals if s.name == name), "")
    return f"{_BRANCH_LABEL[rule_type]} -> retrieve {rule_type} rule ({detail})"


def baseline_stimulation_citation(corpus: Corpus) -> Citation:
    """The deterministic stimulation-protocol citation used when no rule branch fires (R / M).

    Grounds routine/missing-timepoint briefs to the cadence article (§1.2) without any conditional
    retrieval, preserving hard rule 4 (routine emits no ``retrieve_rule``).
    """
    pages = corpus.filter_by(RuleType.STIMULATION)
    chosen = next((p for p in pages if p.article == "§1.2"), None)
    if chosen is None:
        chosen = next((p for p in pages if p.article.lower() != "cover"), None)
    if chosen is None:
        raise AgentAmbiguousError("no stimulation protocol page for the baseline citation")
    return Citation(
        doc_id=chosen.doc_id,
        rule_type=RuleType.STIMULATION,
        page=chosen.page,
        article=chosen.article,
        quote=_first_line(chosen.text),
        score=None,
    )


@dataclass
class AgentRunner:
    """Drives one monitoring run and yields its ``AgentEvent`` trace.

    Construct with the ``run_id`` (the API mints it via ``repo.create_run`` before the SSE stream),
    an :class:`LLMClient`, and the :class:`ToolContext` (bundles retriever, session, thresholds,
    dose table, corpus, id/clock). ``step_budget`` / ``retry_policy`` guard against runaway loops
    and invalid model output; ``max_gap_days`` is the monitoring cadence used for missing-timepoint
    detection.

    ``persist`` (default ``True``) controls whether the runner writes its own step/brief/run rows
    via :mod:`cyclesentinel.db.repo`. The agent lane relies on the default. The API lane builds the
    runner with ``persist=False`` because :func:`cyclesentinel.api.runner.execute_run` owns
    persistence (it stores the full event JSON per step) — so the runner only *emits* events there,
    while still assigning identical monotonic ``step`` numbers via an internal counter.
    """

    llm: LLMClient
    ctx: ToolContext
    run_id: str
    step_budget: StepBudget = field(default_factory=StepBudget)
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    max_gap_days: int = DEFAULT_MAX_GAP_DAYS
    persist: bool = True
    _step: int = field(default=0, init=False, repr=False)

    def _append(self, tool: str, args_summary: str = "", result_summary: str = "") -> int:
        """Return the next 1-based step index; persist the step row too when ``persist`` is set.

        The internal counter guarantees the emitted event ``step`` numbers are identical whether or
        not the runner persists, so the API lane (``persist=False``) yields byte-identical events.
        """
        self._step += 1
        if self.persist:
            repo.append_step(self.ctx.session, self.run_id, tool, args_summary, result_summary)
        return self._step

    async def run(  # noqa: C901 - a single linear pipeline; splitting would obscure the trace order
        self, patient: Patient, result: HormoneResult
    ) -> AsyncIterator[AgentEvent]:
        """Yield the ordered agent trace for ``result`` on ``patient`` (see module docstring)."""
        ctx = self.ctx
        run_id = self.run_id
        try:
            results = repo.list_results(ctx.session, patient.id)
            query = run_query(patient, results)

            # 1. PLAN (LLM turn) -------------------------------------------------------------
            self.step_budget.spend()
            plan = await make_plan(self.llm, patient, results, policy=self.retry_policy)
            step = self._append("plan", patient.id, " | ".join(plan))
            yield PlanEvent(run_id=run_id, step=step, plan=plan)

            # 2. RETRIEVE patient context ----------------------------------------------------
            self.step_budget.spend()
            pctx = await _invoke(
                get_tool("get_patient_context"), ctx, {"patient_id": patient.id}, Patient
            )
            step = self._append("get_patient_context", patient.id, pctx.label)
            yield RetrieveEvent(
                run_id=run_id,
                step=step,
                what="patient_context",
                summary=(
                    f"{pctx.label}: {pctx.protocol}, day {pctx.cycle_day}, "
                    f"AMH {pctx.amh}, AFC {pctx.antral_follicle_count}, PCOS={pctx.pcos_flag}"
                ),
            )

            # 3. RETRIEVE trajectory ---------------------------------------------------------
            self.step_budget.spend()
            traj = await _invoke(
                get_tool("get_trajectory"), ctx, {"patient_id": patient.id}, TrajectoryResult
            )
            step = self._append("get_trajectory", patient.id, f"{traj.count} draws")
            yield RetrieveEvent(
                run_id=run_id,
                step=step,
                what="trajectory",
                summary=f"{traj.count} serial draws through cycle day {patient.cycle_day}",
            )

            # 4. COMPUTE signals (deterministic calculators) ---------------------------------
            self.step_budget.spend()
            signals: list[ComputedSignal] = []
            compute_calls: tuple[tuple[str, dict[str, object]], ...] = (
                ("compute_e2_rate", {"patient_id": patient.id}),
                ("compute_e2_per_follicle", {"result_id": result.id}),
                ("compute_ohss_composite", {"patient_id": patient.id, "result_id": result.id}),
                ("check_progesterone_for_day", {"result_id": result.id}),
            )
            for name, args in compute_calls:
                signal = await _invoke(get_tool(name), ctx, args, ComputedSignal)
                signals.append(signal)
                step = self._append(name, str(args), signal.detail)
                yield ComputeEvent(run_id=run_id, step=step, signal=signal)

            response = compute_response_curve(results, patient.protocol, ctx.thresholds)
            signals.append(response)
            step = self._append("compute_response_curve", patient.id, response.detail)
            yield ComputeEvent(run_id=run_id, step=step, signal=response)

            gap = compute_monitoring_gap(results, self.max_gap_days)
            signals.append(gap)
            step = self._append("compute_monitoring_gap", patient.id, gap.detail)
            yield ComputeEvent(run_id=run_id, step=step, signal=gap)

            # 5. CONDITIONAL BRANCH + RETRIEVE RULE (the "not RAG" core) ----------------------
            retrievals: list[RuleRetrievalResult] = []
            hits: list[RetrievalHit] = []
            for rule_type in branches_for(signals):
                self.step_budget.spend()
                reason = _branch_reason(rule_type, signals)
                step = self._append("branch", str(rule_type), reason)
                yield BranchEvent(run_id=run_id, step=step, reason=reason, rule_type=rule_type)

                rule = await _invoke(
                    get_tool("retrieve_protocol_rule"),
                    ctx,
                    {"query": query, "rule_type": rule_type, "top_k": _RETRIEVAL_TOP_K},
                    RuleRetrievalResult,
                )
                retrievals.append(rule)
                hits.extend(rule.hits)
                step = self._append("retrieve_protocol_rule", str(rule_type), rule.citation.article)
                yield RetrieveRuleEvent(
                    run_id=run_id,
                    step=step,
                    rule_type=rule_type,
                    hits=rule.hits,
                    citation=rule.citation,
                )

            # 6. DECIDE states + escalation --------------------------------------------------
            states = decide_states(signals, retrievals, results)
            escalation_level = escalation_for(states)
            if retrievals:
                citations = [rule.citation for rule in retrievals]
            elif ctx.corpus is not None:
                citations = [baseline_stimulation_citation(ctx.corpus)]
            else:
                citations = []

            # 7. ACTION (dose adjustment OR next-draw timing) --------------------------------
            self.step_budget.spend()
            if DecisionState.POOR_RESPONSE_FLAG in states:
                dose = await _invoke(
                    get_tool("lookup_dose_adjustment"),
                    ctx,
                    {"situation": "poor_response"},
                    DoseAdjustmentResult,
                )
                step = self._append("lookup_dose_adjustment", "poor_response", dose.detail)
                yield ActionEvent(
                    run_id=run_id, step=step, name="dose_adjustment", detail=dose.detail
                )
            else:
                timing = await _invoke(
                    get_tool("compute_next_draw_timing"),
                    ctx,
                    {"patient_id": patient.id},
                    ComputedSignal,
                )
                step = self._append("compute_next_draw_timing", patient.id, timing.detail)
                yield ActionEvent(
                    run_id=run_id, step=step, name="next_draw_timing", detail=timing.detail
                )

            # 8. DRAFT brief (LLM turn) + persist --------------------------------------------
            self.step_budget.spend()
            brief = await draft_brief(
                self.llm,
                ctx,
                patient=patient,
                result=result,
                results=results,
                run_id=run_id,
                states=states,
                citations=citations,
                escalation_level=escalation_level,
                hits=hits,
                policy=self.retry_policy,
            )
            if self.persist:
                repo.save_brief(ctx.session, brief)
            step = self._append(
                "create_monitoring_brief", patient.id, ", ".join(str(s) for s in states)
            )
            yield BriefEvent(run_id=run_id, step=step, brief=brief)

            # 9. ESCALATE (only when there is something to escalate) -------------------------
            if escalation_level != EscalationLevel.NONE:
                escalation = await _invoke(
                    get_tool("escalate_to_biologist"),
                    ctx,
                    {
                        "level": escalation_level,
                        "to": "biologist",
                        "reason": ", ".join(str(s) for s in states),
                    },
                    EscalationResult,
                )
                step = self._append(
                    "escalate_to_biologist", str(escalation_level), escalation.detail
                )
                yield EscalateEvent(
                    run_id=run_id, step=step, level=escalation_level, to=escalation.to
                )

            # 10. DONE -----------------------------------------------------------------------
            if self.persist:
                repo.finish_run(ctx.session, run_id, [str(s) for s in states], brief_id=brief.id)
            yield DoneEvent(run_id=run_id, final_states=states)

        except (AgentAmbiguousError, StepBudgetError) as exc:
            # Fail safe: never a silent "normal" — route the run to human review.
            yield ErrorEvent(run_id=run_id, message=str(exc))
            ambiguous = [DecisionState.AMBIGUOUS_REQUIRES_REVIEW]
            if self.persist:
                repo.finish_run(ctx.session, run_id, [str(s) for s in ambiguous])
            yield DoneEvent(run_id=run_id, final_states=ambiguous)


# ================================================================================================
# API wiring: the ``build_agent_runner`` entrypoint the API lane loads dynamically (api/deps.py).
# ================================================================================================

# loop.py -> agent -> cyclesentinel -> src -> api -> apps -> repo root (parents[5]).
_REPO_ROOT = Path(__file__).resolve().parents[5]
_SYNTHETIC_DIR = _REPO_ROOT / "data" / "synthetic"
# The deterministic replay anchor (matches tests/agent/conftest.py so cassette keys resolve).
_CLOCK_ANCHOR = datetime(2026, 7, 1, 8, 0, tzinfo=UTC)


def build_tool_context(
    session: Session, settings: Settings, retriever: VisualRetriever
) -> ToolContext:
    """Assemble the :class:`ToolContext` the agent loop needs from the on-disk synthetic data.

    Loads the cited thresholds (into the calculator ``Thresholds`` shape), the dose table, and the
    protocol/SOP corpus from ``data/synthetic``, and pairs them with the request-scoped ``session``,
    the mode-selected ``retriever``, and deterministic id/clock sources. ``settings`` is accepted
    for forward-compatibility (data locations are currently repo-relative and deterministic).
    """
    _ = settings  # reserved: data dir is resolved deterministically from the repo root today
    return ToolContext(
        session=session,
        retriever=retriever,
        thresholds=load_thresholds(_SYNTHETIC_DIR / "thresholds.json"),
        dose_table=load_dose_rules(_SYNTHETIC_DIR / "dose_tables.json"),
        corpus=load_corpus(_SYNTHETIC_DIR / "corpus"),
        ids=IdFactory("id"),
        clock=Clock(_CLOCK_ANCHOR),
    )


@dataclass
class _ApiAgentRunner:
    """Adapter matching the API's runner protocol (``run(run_id, patient_id, result_id)``).

    Loads the patient + triggering result from the session, then delegates to the real
    :class:`AgentRunner` with ``persist=False`` (``execute_run`` owns persistence). Loads cleanly to
    a human-review ``error``/``done`` pair when either row is missing, honouring the fail-safe rule.
    """

    llm: LLMClient
    ctx: ToolContext

    async def run(self, run_id: str, patient_id: str, result_id: str) -> AsyncIterator[AgentEvent]:
        patient = repo.get_patient(self.ctx.session, patient_id)
        result = repo.get_result(self.ctx.session, result_id)
        if patient is None or result is None:
            missing = patient_id if patient is None else result_id
            yield ErrorEvent(run_id=run_id, message=f"unknown run subject: {missing!r}")
            yield DoneEvent(run_id=run_id, final_states=[DecisionState.AMBIGUOUS_REQUIRES_REVIEW])
            return
        # Namespace minted ids by the run so persisted brief ids stay unique across runs sharing
        # one database (the deterministic per-run counter alone would collide as ``brief-0001``).
        self.ctx.ids = IdFactory("id", namespace=f"{run_id[:8]}-")
        runner = AgentRunner(llm=self.llm, ctx=self.ctx, run_id=run_id, persist=False)
        async for event in runner.run(patient, result):
            yield event


def build_agent_runner(
    *,
    session: Session,
    settings: Settings,
    llm: LLMClient,
    retriever: VisualRetriever,
) -> _ApiAgentRunner:
    """The entrypoint ``api/deps.make_runner_factory`` imports to drive real runs over the API.

    Builds the tool context bound to ``session`` and returns an adapter whose
    ``run(run_id, patient_id, result_id)`` yields the ordered :data:`AgentEvent` trace.
    """
    ctx = build_tool_context(session, settings, retriever)
    return _ApiAgentRunner(llm=llm, ctx=ctx)
