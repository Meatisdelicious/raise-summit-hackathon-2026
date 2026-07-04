"""FastAPI routers and the SSE agent-trace endpoint, aggregated under the ``/api`` prefix."""

from __future__ import annotations

from fastapi import APIRouter

from cyclesentinel.api import briefs, demo, health, patients, runs

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(patients.router)
api_router.include_router(runs.router)
api_router.include_router(briefs.router)
api_router.include_router(demo.router)

__all__ = ["api_router"]
