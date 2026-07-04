"""Typed persistence functions mapping ORM rows to/from the Pydantic contract models.

Every function takes an explicit :class:`~sqlalchemy.orm.Session` so callers own the transaction
boundary (see :func:`cyclesentinel.db.session.get_session`). Return types are the Pydantic models
from :mod:`cyclesentinel.schemas` — never ORM rows — so nothing downstream depends on SQLAlchemy.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from cyclesentinel.db.models import BriefRow, PatientRow, ResultRow, RunRow, StepRow
from cyclesentinel.schemas import (
    Citation,
    HormoneResult,
    MonitoringBrief,
    Patient,
    RunSummary,
)

# --- ORM -> Pydantic mappers -------------------------------------------------------------------


def _to_patient(row: PatientRow) -> Patient:
    return Patient(
        id=row.id,
        label=row.label,
        protocol=row.protocol,  # type: ignore[arg-type]
        cycle_day=row.cycle_day,
        amh=row.amh,
        antral_follicle_count=row.antral_follicle_count,
        pcos_flag=row.pcos_flag,
    )


def _to_result(row: ResultRow) -> HormoneResult:
    return HormoneResult(
        id=row.id,
        patient_id=row.patient_id,
        cycle_day=row.cycle_day,
        drawn_at=row.drawn_at,
        e2=row.e2,
        lh=row.lh,
        progesterone=row.progesterone,
        fsh=row.fsh,
        hcg=row.hcg,
        mature_follicle_count=row.mature_follicle_count,
    )


def _to_brief(row: BriefRow) -> MonitoringBrief:
    return MonitoringBrief(
        id=row.id,
        patient_id=row.patient_id,
        result_id=row.result_id,
        run_id=row.run_id,
        states=list(row.states),  # type: ignore[arg-type]
        interpretation=row.interpretation,
        recommended_action=row.recommended_action,
        citations=[Citation.model_validate(c) for c in row.citations],
        escalation_level=row.escalation_level,  # type: ignore[arg-type]
        validated_by=row.validated_by,
        validated_at=row.validated_at,
        created_at=row.created_at,
    )


def _to_run(row: RunRow) -> RunSummary:
    return RunSummary(
        run_id=row.run_id,
        patient_id=row.patient_id,
        result_id=row.result_id,
        final_states=list(row.final_states),  # type: ignore[arg-type]
        brief_id=row.brief_id,
        started_at=row.started_at,
        finished_at=row.finished_at,
        step_count=row.step_count,
    )


# --- Patients & results ------------------------------------------------------------------------


def get_patient(session: Session, patient_id: str) -> Patient | None:
    """Return the patient with ``patient_id``, or ``None`` if unknown."""
    row = session.get(PatientRow, patient_id)
    return _to_patient(row) if row is not None else None


def list_patients(session: Session) -> list[Patient]:
    """Return all patients, ordered by id for a stable demo listing."""
    rows = session.scalars(select(PatientRow).order_by(PatientRow.id)).all()
    return [_to_patient(r) for r in rows]


def list_results(session: Session, patient_id: str) -> list[HormoneResult]:
    """Return the patient's serial results ordered by ``cycle_day`` (the trajectory)."""
    rows = session.scalars(
        select(ResultRow)
        .where(ResultRow.patient_id == patient_id)
        .order_by(ResultRow.cycle_day, ResultRow.drawn_at)
    ).all()
    return [_to_result(r) for r in rows]


def get_result(session: Session, result_id: str) -> HormoneResult | None:
    """Return the single result with ``result_id``, or ``None`` if unknown."""
    row = session.get(ResultRow, result_id)
    return _to_result(row) if row is not None else None


def latest_result(session: Session, patient_id: str) -> HormoneResult | None:
    """Return the patient's most advanced result (highest ``cycle_day``), or ``None``."""
    row = session.scalars(
        select(ResultRow)
        .where(ResultRow.patient_id == patient_id)
        .order_by(ResultRow.cycle_day.desc(), ResultRow.drawn_at.desc())
        .limit(1)
    ).first()
    return _to_result(row) if row is not None else None


# --- Briefs ------------------------------------------------------------------------------------


def save_brief(session: Session, brief: MonitoringBrief) -> MonitoringBrief:
    """Insert or update ``brief`` (keyed by ``brief.id``) and return the persisted model."""
    row = session.get(BriefRow, brief.id)
    citations = [c.model_dump(mode="json") for c in brief.citations]
    if row is None:
        row = BriefRow(id=brief.id)
        session.add(row)
    row.patient_id = brief.patient_id
    row.result_id = brief.result_id
    row.run_id = brief.run_id
    row.states = [str(s) for s in brief.states]
    row.interpretation = brief.interpretation
    row.recommended_action = brief.recommended_action
    row.citations = citations
    row.escalation_level = str(brief.escalation_level)
    row.validated_by = brief.validated_by
    row.validated_at = brief.validated_at
    row.created_at = brief.created_at
    session.flush()
    return _to_brief(row)


def latest_brief(session: Session, patient_id: str) -> MonitoringBrief | None:
    """Return the patient's most recent brief by ``created_at``, or ``None``."""
    row = session.scalars(
        select(BriefRow)
        .where(BriefRow.patient_id == patient_id)
        .order_by(BriefRow.created_at.desc())
        .limit(1)
    ).first()
    return _to_brief(row) if row is not None else None


def get_brief(session: Session, brief_id: str) -> MonitoringBrief | None:
    """Return the brief with ``brief_id``, or ``None`` if unknown."""
    row = session.get(BriefRow, brief_id)
    return _to_brief(row) if row is not None else None


def validate_brief(
    session: Session,
    brief_id: str,
    validated_by: str,
    edits: dict[str, object] | None = None,
) -> MonitoringBrief | None:
    """Stamp validation (applying whitelisted ``edits``); ``None`` if the brief is absent."""
    row = session.get(BriefRow, brief_id)
    if row is None:
        return None
    row.validated_by = validated_by
    row.validated_at = datetime.now(UTC)
    if edits:
        if "interpretation" in edits and isinstance(edits["interpretation"], str):
            row.interpretation = edits["interpretation"]
        if "recommended_action" in edits and isinstance(edits["recommended_action"], str):
            row.recommended_action = edits["recommended_action"]
        if "escalation_level" in edits and isinstance(edits["escalation_level"], str):
            row.escalation_level = edits["escalation_level"]
    session.flush()
    return _to_brief(row)


def reject_brief(
    session: Session, brief_id: str, validated_by: str, reason: str
) -> MonitoringBrief | None:
    """Record a rejection (escalate to review, note the reason); ``None`` if the brief is absent."""
    row = session.get(BriefRow, brief_id)
    if row is None:
        return None
    row.validated_by = validated_by
    row.validated_at = datetime.now(UTC)
    row.recommended_action = f"[REJECTED by {validated_by}: {reason}] {row.recommended_action}"
    if "AMBIGUOUS_REQUIRES_REVIEW" not in row.states:
        row.states = [*row.states, "AMBIGUOUS_REQUIRES_REVIEW"]
    session.flush()
    return _to_brief(row)


# --- Runs & steps ------------------------------------------------------------------------------


def create_run(session: Session, patient_id: str, result_id: str) -> RunSummary:
    """Create a fresh run for ``(patient_id, result_id)`` and return its summary."""
    row = RunRow(
        run_id=uuid.uuid4().hex,
        patient_id=patient_id,
        result_id=result_id,
        final_states=[],
        brief_id=None,
        started_at=datetime.now(UTC),
        finished_at=None,
        step_count=0,
    )
    session.add(row)
    session.flush()
    return _to_run(row)


def get_run(session: Session, run_id: str) -> RunSummary | None:
    """Return the run summary for ``run_id``, or ``None`` if unknown."""
    row = session.get(RunRow, run_id)
    return _to_run(row) if row is not None else None


def append_step(
    session: Session,
    run_id: str,
    tool: str,
    args_summary: str = "",
    result_summary: str = "",
    latency_ms: float | None = None,
) -> int:
    """Append one ordered step to ``run_id`` and return its 1-based step index.

    Increments the run's ``step_count``; a missing run is a no-op returning ``0``.
    """
    run = session.get(RunRow, run_id)
    if run is None:
        return 0
    step_index = run.step_count + 1
    session.add(
        StepRow(
            run_id=run_id,
            step=step_index,
            tool=tool,
            args_summary=args_summary,
            result_summary=result_summary,
            latency_ms=latency_ms,
            created_at=datetime.now(UTC),
        )
    )
    run.step_count = step_index
    session.flush()
    return step_index


def finish_run(
    session: Session,
    run_id: str,
    final_states: list[str],
    brief_id: str | None = None,
) -> RunSummary | None:
    """Close ``run_id`` with its final states and optional brief id; ``None`` if unknown."""
    row = session.get(RunRow, run_id)
    if row is None:
        return None
    row.final_states = [str(s) for s in final_states]
    row.brief_id = brief_id
    row.finished_at = datetime.now(UTC)
    session.flush()
    return _to_run(row)
