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


def plan_messages(query: str) -> list[ChatMessage]:
    """The single-turn planning prompt (returns a JSON ``{"plan": [...]}`` object)."""
    return [ChatMessage(role="user", content=f"Plan how to triage this result:\n{query}")]


def brief_messages(query: str) -> list[ChatMessage]:
    """The single-turn brief prompt (returns JSON ``{"interpretation", "recommended_action"}``)."""
    return [
        ChatMessage(role="user", content=f"Write the cited monitoring brief prose for:\n{query}")
    ]
