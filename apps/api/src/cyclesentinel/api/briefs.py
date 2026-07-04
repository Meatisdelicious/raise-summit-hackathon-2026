"""Human-in-the-loop brief validation / rejection (CONTRACTS.md §3).

Every brief is internal triage: a biologist validates or rejects before it reaches the clinic.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from cyclesentinel.api.deps import SessionDep
from cyclesentinel.db import repo
from cyclesentinel.schemas import MonitoringBrief, RejectBody, ValidateBody

router = APIRouter(tags=["briefs"])


@router.post("/briefs/{brief_id}/validate")
def validate_brief(brief_id: str, body: ValidateBody, session: SessionDep) -> MonitoringBrief:
    """Stamp validation (applying whitelisted edits) and return the updated brief, or 404."""
    brief = repo.validate_brief(session, brief_id, body.validated_by, body.edits)
    if brief is None:
        raise HTTPException(status_code=404, detail="unknown brief")
    return brief


@router.post("/briefs/{brief_id}/reject")
def reject_brief(brief_id: str, body: RejectBody, session: SessionDep) -> MonitoringBrief:
    """Record a rejection (routes to review) and return the updated brief, or 404."""
    brief = repo.reject_brief(session, brief_id, body.validated_by, body.reason)
    if brief is None:
        raise HTTPException(status_code=404, detail="unknown brief")
    return brief
