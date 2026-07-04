"""Liveness + readiness probes (CONTRACTS.md §3)."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Response for ``GET /health``."""

    status: Literal["ok"]


class ReadyResponse(BaseModel):
    """Response for ``GET /ready``."""

    ready: bool


@router.get("/health")
def health() -> HealthResponse:
    """Liveness: the app is up."""
    return HealthResponse(status="ok")


@router.get("/ready")
def ready(request: Request) -> ReadyResponse:
    """Readiness: the DB session factory has been wired by the lifespan startup."""
    is_ready = getattr(request.app.state, "session_factory", None) is not None
    return ReadyResponse(ready=is_ready)
