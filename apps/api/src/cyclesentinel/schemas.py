"""Core API objects — Pydantic v2 models mirroring ``docs/CONTRACTS.md`` §2/§3.

Field names match the TypeScript interfaces byte-for-byte (the contract-drift test enforces this).
Datetimes serialize to ISO-8601 strings via Pydantic's default JSON encoding.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from cyclesentinel.enums import (
    DecisionState,
    EscalationLevel,
    Protocol,
    RuleType,
)


class Patient(BaseModel):
    """A synthetic patient in IVF stimulation."""

    model_config = ConfigDict(use_enum_values=True)

    id: str
    label: str
    protocol: Protocol
    cycle_day: int
    amh: float
    antral_follicle_count: int
    pcos_flag: bool


class HormoneResult(BaseModel):
    """A single serial hormone draw (one point on the trajectory)."""

    id: str
    patient_id: str
    cycle_day: int
    drawn_at: datetime
    e2: float | None
    lh: float | None
    progesterone: float | None
    fsh: float | None = None
    hcg: float | None = None
    mature_follicle_count: int | None = None


class Citation(BaseModel):
    """A grounded reference to a protocol/SOP article on a retrieved page."""

    model_config = ConfigDict(use_enum_values=True)

    doc_id: str
    rule_type: RuleType
    page: int
    article: str
    quote: str
    score: float | None = None


class RetrievalHit(BaseModel):
    """A single page returned by the visual retriever (Vultron Prime-8B)."""

    model_config = ConfigDict(use_enum_values=True)

    doc_id: str
    rule_type: RuleType
    page: int
    score: float
    text: str
    article: str


class ComputedSignal(BaseModel):
    """The output of one deterministic calculator."""

    name: str
    value: float | str
    detail: str
    tripped: bool


class MonitoringBrief(BaseModel):
    """The cited monitoring brief a human validates before it reaches the clinic."""

    model_config = ConfigDict(use_enum_values=True)

    id: str
    patient_id: str
    result_id: str
    run_id: str
    states: list[DecisionState]
    interpretation: str
    recommended_action: str
    citations: list[Citation]
    escalation_level: EscalationLevel
    validated_by: str | None = None
    validated_at: datetime | None = None
    created_at: datetime


class RunSummary(BaseModel):
    """Summary of a single agent run."""

    model_config = ConfigDict(use_enum_values=True)

    run_id: str
    patient_id: str
    result_id: str
    final_states: list[DecisionState]
    brief_id: str | None = None
    started_at: datetime
    finished_at: datetime | None = None
    step_count: int


# --- Request bodies (docs/CONTRACTS.md §3) -----------------------------------------------------


class StartRunBody(BaseModel):
    """Body for ``POST /api/patients/{id}/runs`` (defaults to the newest result)."""

    result_id: str | None = None


class ValidateBody(BaseModel):
    """Body for ``POST /api/briefs/{id}/validate``."""

    validated_by: str
    edits: dict[str, object] | None = None


class RejectBody(BaseModel):
    """Body for ``POST /api/briefs/{id}/reject``."""

    validated_by: str
    reason: str
