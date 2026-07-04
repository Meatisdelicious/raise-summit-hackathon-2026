"""Contract-drift tripwire.

Parses the TypeScript enum / interface / event-union blocks out of ``docs/CONTRACTS.md`` and asserts
that the Pydantic models in :mod:`cyclesentinel.schemas` and :mod:`cyclesentinel.events`, and the
enums in :mod:`cyclesentinel.enums`, match them byte-for-byte on:

* enum member values (exact, ordered),
* field-name sets per model,
* per-field nullability (a TS ``| null`` type or an optional ``field?`` maps to a Python type that
  admits ``None``; a required non-null TS field maps to one that does not).

If the frozen contract and the backend drift apart, this test fails loudly.
"""

from __future__ import annotations

import re
from pathlib import Path
from types import UnionType
from typing import Union, get_args, get_origin

import pytest
from pydantic import BaseModel

from cyclesentinel import enums, events, schemas


def _contracts_path() -> Path:
    """Locate ``docs/CONTRACTS.md`` by walking up from this test file."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "docs" / "CONTRACTS.md"
        if candidate.exists():
            return candidate
    raise FileNotFoundError("docs/CONTRACTS.md not found above test file")


CONTRACTS = _contracts_path().read_text(encoding="utf-8")


# --------------------------------------------------------------------------------------------------
# TS parsing helpers
# --------------------------------------------------------------------------------------------------


def _strip_comments(text: str) -> str:
    """Remove ``// ...`` line comments so they can't bleed across ``;`` splits."""
    return re.sub(r"//[^\n]*", "", text)


def parse_enum(name: str) -> list[str]:
    """Return the ordered string literal values of ``export type <name> = "a" | "b" | ...;``."""
    match = re.search(rf"export type {name}\s*=\s*(.*?);", CONTRACTS, re.DOTALL)
    assert match, f"enum {name} not found in CONTRACTS.md"
    return re.findall(r'"([^"]+)"', match.group(1))


def parse_interface(name: str) -> dict[str, bool]:
    """Return ``{field_name: nullable}`` for ``export interface <name> { ... }``.

    ``nullable`` is True when the TS field is optional (``field?``) or its type includes ``null``.
    """
    match = re.search(rf"export interface {name}\s*\{{(.*?)\}}", CONTRACTS, re.DOTALL)
    assert match, f"interface {name} not found in CONTRACTS.md"
    return _parse_fields(match.group(1))


def _parse_fields(body: str) -> dict[str, bool]:
    fields: dict[str, bool] = {}
    for raw in _strip_comments(body).split(";"):
        line = raw.strip()
        if not line or ":" not in line:
            continue
        key_part, type_part = line.split(":", 1)
        key = key_part.strip()
        optional = key.endswith("?")
        key = key.rstrip("?").strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            continue
        nullable = optional or "null" in type_part
        fields[key] = nullable
    return fields


def parse_event_variants() -> dict[str, dict[str, bool]]:
    """Return ``{type_literal: {field_name: nullable}}`` for the AgentEvent union."""
    # Each variant contains internal ``;`` mid-line, so anchor on the ``;`` that ends the
    # statement (the only one immediately followed by end-of-line).
    match = re.search(
        r"export type AgentEvent\s*=\s*(.*?);\s*$", CONTRACTS, re.DOTALL | re.MULTILINE
    )
    assert match, "AgentEvent union not found in CONTRACTS.md"
    variants: dict[str, dict[str, bool]] = {}
    for block in re.findall(r"\{(.*?)\}", match.group(1), re.DOTALL):
        fields = _parse_fields(block)
        tag = re.search(r'type"?\s*:\s*"([^"]+)"', block)
        assert tag, f"event variant missing a type discriminator: {block!r}"
        variants[tag.group(1)] = fields
    return variants


# --------------------------------------------------------------------------------------------------
# Pydantic introspection helpers
# --------------------------------------------------------------------------------------------------


def _allows_none(annotation: object) -> bool:
    if annotation is type(None):
        return True
    if get_origin(annotation) in (Union, UnionType):
        return any(arg is type(None) for arg in get_args(annotation))
    return False


def model_fields(model: type[BaseModel]) -> dict[str, bool]:
    """Return ``{field_name: allows_none}`` for a Pydantic model."""
    return {name: _allows_none(info.annotation) for name, info in model.model_fields.items()}


# --------------------------------------------------------------------------------------------------
# Enums
# --------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("ts_name", "enum_cls"),
    [
        ("Protocol", enums.Protocol),
        ("DecisionState", enums.DecisionState),
        ("EscalationLevel", enums.EscalationLevel),
        ("RuleType", enums.RuleType),
    ],
)
def test_enum_values_match(ts_name: str, enum_cls: type[enums.Protocol]) -> None:
    ts_values = parse_enum(ts_name)
    py_values = [member.value for member in enum_cls]
    assert py_values == ts_values, f"{ts_name} enum drift: {py_values} != {ts_values}"


# --------------------------------------------------------------------------------------------------
# Core object interfaces (schemas.py)
# --------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("ts_name", "model"),
    [
        ("Patient", schemas.Patient),
        ("HormoneResult", schemas.HormoneResult),
        ("Citation", schemas.Citation),
        ("RetrievalHit", schemas.RetrievalHit),
        ("ComputedSignal", schemas.ComputedSignal),
        ("MonitoringBrief", schemas.MonitoringBrief),
        ("RunSummary", schemas.RunSummary),
    ],
)
def test_schema_matches_interface(ts_name: str, model: type[BaseModel]) -> None:
    ts_fields = parse_interface(ts_name)
    py_fields = model_fields(model)

    assert set(py_fields) == set(ts_fields), (
        f"{ts_name} field-name drift: python={sorted(py_fields)} ts={sorted(ts_fields)}"
    )
    for field, nullable in ts_fields.items():
        assert py_fields[field] == nullable, (
            f"{ts_name}.{field} nullability drift: python_allows_none={py_fields[field]} "
            f"ts_nullable={nullable}"
        )


# --------------------------------------------------------------------------------------------------
# AgentEvent union (events.py)
# --------------------------------------------------------------------------------------------------

_EVENT_MODELS: dict[str, type[BaseModel]] = {
    "plan": events.PlanEvent,
    "retrieve": events.RetrieveEvent,
    "compute": events.ComputeEvent,
    "branch": events.BranchEvent,
    "retrieve_rule": events.RetrieveRuleEvent,
    "action": events.ActionEvent,
    "brief": events.BriefEvent,
    "escalate": events.EscalateEvent,
    "error": events.ErrorEvent,
    "done": events.DoneEvent,
}


def test_event_union_is_complete() -> None:
    ts_variants = parse_event_variants()
    assert set(ts_variants) == set(_EVENT_MODELS), (
        f"AgentEvent variant drift: python={sorted(_EVENT_MODELS)} ts={sorted(ts_variants)}"
    )


@pytest.mark.parametrize("tag", sorted(_EVENT_MODELS))
def test_event_variant_matches(tag: str) -> None:
    ts_variants = parse_event_variants()
    ts_fields = ts_variants[tag]
    py_fields = model_fields(_EVENT_MODELS[tag])

    assert set(py_fields) == set(ts_fields), (
        f"{tag} event field-name drift: python={sorted(py_fields)} ts={sorted(ts_fields)}"
    )
    for field, nullable in ts_fields.items():
        assert py_fields[field] == nullable, (
            f"{tag} event field '{field}' nullability drift: "
            f"python_allows_none={py_fields[field]} ts_nullable={nullable}"
        )


def test_sse_format_frames_compact_json() -> None:
    event = events.DoneEvent(run_id="r1", final_states=[enums.DecisionState.ROUTINE_CONTINUE])
    frame = events.sse_format(event)
    assert frame.startswith(b"data: ")
    assert frame.endswith(b"\n\n")
    assert b"\n" not in frame[6:-2]  # payload itself is single-line / compact
