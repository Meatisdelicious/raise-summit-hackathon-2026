"""Patient + trajectory + latest-brief read endpoints (CONTRACTS.md §3)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from cyclesentinel.api.deps import SessionDep
from cyclesentinel.db import repo
from cyclesentinel.schemas import HormoneResult, MonitoringBrief, Patient

router = APIRouter(tags=["patients"])


@router.get("/patients")
def list_patients(session: SessionDep) -> list[Patient]:
    """Return every synthetic patient."""
    return repo.list_patients(session)


@router.get("/patients/{patient_id}")
def get_patient(patient_id: str, session: SessionDep) -> Patient:
    """Return one patient or 404."""
    patient = repo.get_patient(session, patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="unknown patient")
    return patient


@router.get("/patients/{patient_id}/results")
def list_results(patient_id: str, session: SessionDep) -> list[HormoneResult]:
    """Return the patient's serial results (the trajectory), ordered by cycle day."""
    if repo.get_patient(session, patient_id) is None:
        raise HTTPException(status_code=404, detail="unknown patient")
    return repo.list_results(session, patient_id)


@router.get("/patients/{patient_id}/latest-brief")
def latest_brief(patient_id: str, session: SessionDep) -> MonitoringBrief | None:
    """Return the patient's most recent monitoring brief, or ``null`` if none exists yet."""
    if repo.get_patient(session, patient_id) is None:
        raise HTTPException(status_code=404, detail="unknown patient")
    return repo.latest_brief(session, patient_id)
