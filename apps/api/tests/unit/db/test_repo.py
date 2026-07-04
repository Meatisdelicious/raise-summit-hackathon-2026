"""Round-trip tests for :mod:`cyclesentinel.db.repo` (ORM <-> Pydantic, JSON cols, runs/steps)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from cyclesentinel.db import repo
from cyclesentinel.db.models import PatientRow, ResultRow
from cyclesentinel.enums import DecisionState, EscalationLevel, Protocol, RuleType
from cyclesentinel.schemas import Citation, MonitoringBrief


def _seed_patient(session: Session, patient_id: str = "pat_k") -> None:
    session.add(
        PatientRow(
            id=patient_id,
            label="Patient K",
            protocol=Protocol.ANTAGONIST.value,
            cycle_day=8,
            amh=4.2,
            antral_follicle_count=24,
            pcos_flag=True,
        )
    )
    # Insert out of cycle-day order to prove list_results sorts.
    for rid, day, e2 in (("res_2", 8, 3200.0), ("res_0", 4, 400.0), ("res_1", 6, 1200.0)):
        session.add(
            ResultRow(
                id=rid,
                patient_id=patient_id,
                cycle_day=day,
                drawn_at=datetime(2026, 1, day, 8, 0, tzinfo=UTC),
                e2=e2,
                lh=3.1,
                progesterone=0.8,
                fsh=None,
                hcg=None,
                mature_follicle_count=day,
            )
        )
    session.flush()


def _make_brief(brief_id: str = "brief_1", run_id: str = "run_1") -> MonitoringBrief:
    return MonitoringBrief(
        id=brief_id,
        patient_id="pat_k",
        result_id="res_2",
        run_id=run_id,
        states=[DecisionState.OHSS_RISK_ESCALATE, DecisionState.PREMATURE_LUTEINIZATION_FLAG],
        interpretation="Steep E2 rise with borderline P4 for day 8.",
        recommended_action="Consider coasting; cite OHSS SOP.",
        citations=[
            Citation(
                doc_id="ohss_sop",
                rule_type=RuleType.OHSS,
                page=4,
                article="§4.2",
                quote="Coast if E2 rises steeply.",
                score=0.91,
            )
        ],
        escalation_level=EscalationLevel.URGENT,
        created_at=datetime(2026, 1, 8, 9, 0, tzinfo=UTC),
    )


def test_get_and_list_patients(session: Session) -> None:
    assert repo.get_patient(session, "missing") is None
    _seed_patient(session)
    patient = repo.get_patient(session, "pat_k")
    assert patient is not None
    assert patient.label == "Patient K"
    assert patient.protocol == Protocol.ANTAGONIST
    assert patient.pcos_flag is True
    assert [p.id for p in repo.list_patients(session)] == ["pat_k"]


def test_list_results_ordered_by_cycle_day(session: Session) -> None:
    _seed_patient(session)
    results = repo.list_results(session, "pat_k")
    assert [r.cycle_day for r in results] == [4, 6, 8]
    assert results[-1].e2 == 3200.0
    latest = repo.latest_result(session, "pat_k")
    assert latest is not None and latest.id == "res_2"


def test_save_and_read_brief_json_columns(session: Session) -> None:
    _seed_patient(session)
    saved = repo.save_brief(session, _make_brief())
    assert saved.id == "brief_1"

    fetched = repo.get_brief(session, "brief_1")
    assert fetched is not None
    # states[] round-trips through the JSON column as DecisionState values.
    assert fetched.states == [
        DecisionState.OHSS_RISK_ESCALATE,
        DecisionState.PREMATURE_LUTEINIZATION_FLAG,
    ]
    # citations[] round-trips through JSON into Citation models.
    assert len(fetched.citations) == 1
    assert fetched.citations[0].doc_id == "ohss_sop"
    assert fetched.citations[0].page == 4
    assert fetched.citations[0].score == 0.91
    assert fetched.escalation_level == EscalationLevel.URGENT

    latest = repo.latest_brief(session, "pat_k")
    assert latest is not None and latest.id == "brief_1"


def test_save_brief_upsert(session: Session) -> None:
    _seed_patient(session)
    repo.save_brief(session, _make_brief())
    edited = _make_brief()
    edited.interpretation = "Updated interpretation."
    repo.save_brief(session, edited)
    fetched = repo.get_brief(session, "brief_1")
    assert fetched is not None
    assert fetched.interpretation == "Updated interpretation."


def test_validate_brief(session: Session) -> None:
    _seed_patient(session)
    repo.save_brief(session, _make_brief())
    assert repo.validate_brief(session, "missing", "dr.bio") is None

    validated = repo.validate_brief(
        session,
        "brief_1",
        "dr.bio",
        edits={"recommended_action": "Freeze-all."},
    )
    assert validated is not None
    assert validated.validated_by == "dr.bio"
    assert validated.validated_at is not None
    assert validated.recommended_action == "Freeze-all."


def test_reject_brief(session: Session) -> None:
    _seed_patient(session)
    repo.save_brief(session, _make_brief())
    rejected = repo.reject_brief(session, "brief_1", "dr.bio", "insufficient data")
    assert rejected is not None
    assert rejected.validated_by == "dr.bio"
    assert DecisionState.AMBIGUOUS_REQUIRES_REVIEW in rejected.states
    assert "insufficient data" in rejected.recommended_action


def test_run_lifecycle_with_steps(session: Session) -> None:
    _seed_patient(session)
    run = repo.create_run(session, "pat_k", "res_2")
    assert run.step_count == 0
    assert run.finished_at is None

    assert repo.append_step(session, run.run_id, "get_patient_context") == 1
    assert repo.append_step(session, run.run_id, "get_trajectory") == 2
    assert (
        repo.append_step(session, run.run_id, "compute_ohss_composite", "e2=3200", "tripped") == 3
    )
    # Appending to an unknown run is a no-op.
    assert repo.append_step(session, "nope", "x") == 0

    mid = repo.get_run(session, run.run_id)
    assert mid is not None and mid.step_count == 3

    finished = repo.finish_run(
        session,
        run.run_id,
        [DecisionState.OHSS_RISK_ESCALATE.value],
        brief_id="brief_1",
    )
    assert finished is not None
    assert finished.final_states == [DecisionState.OHSS_RISK_ESCALATE]
    assert finished.brief_id == "brief_1"
    assert finished.finished_at is not None
    assert finished.step_count == 3


def test_finish_and_get_unknown_run(session: Session) -> None:
    assert repo.get_run(session, "nope") is None
    assert repo.finish_run(session, "nope", []) is None
