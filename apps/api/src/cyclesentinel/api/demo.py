"""Demo state reset (CONTRACTS.md §3)."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from cyclesentinel.api.deps import BusDep, SessionDep
from cyclesentinel.db.seed import reset_demo

router = APIRouter(tags=["demo"])


class ResetResponse(BaseModel):
    """Response for ``POST /demo/reset``."""

    ok: bool


@router.post("/demo/reset")
def reset(session: SessionDep, bus: BusDep) -> ResetResponse:
    """Wipe runtime tables, reseed the synthetic fixtures, and clear buffered run traces."""
    reset_demo(session)
    session.commit()
    bus.clear()
    return ResetResponse(ok=True)
