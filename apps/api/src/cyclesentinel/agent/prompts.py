"""The frozen LLM request framing (the single alignment point with the replay cassettes).

The agent talks to the text LLM (Kimi K2) exactly twice per run — once to plan, once to write the
brief prose — and the visual retriever with the same trajectory ``query`` string. Those requests
are content-hashed into cassette filenames (``cyclesentinel.inference.cassette``), so the strings
built here must match ``scripts/record_cassettes.py::build_request_specs`` byte-for-byte. Change
one, re-run ``record_cassettes.py --seed``, and keep the other in lock-step.
"""

from __future__ import annotations

from collections.abc import Sequence

from cyclesentinel.inference.base import ChatMessage
from cyclesentinel.schemas import HormoneResult, Patient


def run_query(patient: Patient, results: Sequence[HormoneResult]) -> str:
    """A compact one-line framing of the case (patient baseline + E2 trajectory).

    Shared by both LLM turns and every conditional retrieval so a case keys deterministically. Only
    draws that carry an E2 value contribute to the series; results are taken in trajectory order.
    """
    series = ", ".join(f"d{r.cycle_day}={r.e2}pg/mL" for r in results if r.e2 is not None)
    return (
        f"{patient.label} ({patient.protocol}, cycle day {patient.cycle_day}, "
        f"PCOS={patient.pcos_flag}). E2 trajectory: {series}."
    )


_PLAN_SYSTEM = (
    "You are the planning step of an internal clinical-operations triage agent for IVF "
    "ovarian-stimulation monitoring (a lab-biologist decision-support tool, never patient-facing). "
    'Output ONLY a JSON object of the exact form {"plan": ["step", ...]} with 3 to 6 short '
    "operational steps for triaging this result (rebuild the trajectory, compute the deterministic "
    "signals, retrieve the governing protocol/SOP rule when a signal trips, draft a cited brief). "
    "Use operational language only: do NOT prescribe treatment, drugs, or doses. Clinical "
    "decisions are made by the biologist. No prose, no markdown, no code fences. JSON only."
)

_BRIEF_SYSTEM = (
    "You are the brief-writing step of an internal clinical-operations triage agent for IVF "
    "ovarian-stimulation monitoring (a lab-biologist decision-support tool, never patient-facing). "
    'Output ONLY a JSON object of the exact form {"interpretation": "...", "recommended_action": '
    '"..."}. Write concise internal-triage prose for a lab biologist. "interpretation" reads the '
    'trajectory in context; "recommended_action" is an OPERATIONAL next step (e.g. escalate to the '
    "biologist, request a repeat/overdue draw, or shorten the monitoring interval). Do NOT "
    "prescribe or name treatments or drug doses; every clinical decision needs biologist "
    "validation. No markdown, no code fences. JSON only."
)


def plan_messages(query: str) -> list[ChatMessage]:
    """The single-turn planning prompt (returns a JSON ``{"plan": [...]}`` object)."""
    return [
        ChatMessage(role="system", content=_PLAN_SYSTEM),
        ChatMessage(role="user", content=f"Plan how to triage this result:\n{query}"),
    ]


def brief_messages(query: str) -> list[ChatMessage]:
    """The single-turn brief prompt (returns JSON ``{"interpretation", "recommended_action"}``)."""
    return [
        ChatMessage(role="system", content=_BRIEF_SYSTEM),
        ChatMessage(role="user", content=f"Write the internal monitoring brief for:\n{query}"),
    ]
