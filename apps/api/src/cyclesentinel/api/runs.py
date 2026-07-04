"""Agent-run lifecycle: start a run, read its summary, stream its SSE trace (CONTRACTS.md §3/§4)."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from starlette.responses import StreamingResponse

from cyclesentinel.api.deps import (
    BusDep,
    RunnerDep,
    SessionDep,
    SessionFactoryDep,
    TasksDep,
)
from cyclesentinel.api.runner import execute_run, stream_live, stream_persisted
from cyclesentinel.db import repo
from cyclesentinel.schemas import RunSummary, StartRunBody

router = APIRouter(tags=["runs"])


class RunStarted(BaseModel):
    """Response for ``POST /patients/{id}/runs``."""

    run_id: str


@router.post("/patients/{patient_id}/runs")
async def start_run(
    patient_id: str,
    body: StartRunBody,
    session: SessionDep,
    session_factory: SessionFactoryDep,
    bus: BusDep,
    tasks: TasksDep,
    runner_factory: RunnerDep,
) -> RunStarted:
    """Start an agent run on the chosen (or newest) result and return its ``run_id``."""
    if repo.get_patient(session, patient_id) is None:
        raise HTTPException(status_code=404, detail="unknown patient")

    if body.result_id is not None:
        result = repo.get_result(session, body.result_id)
        if result is None or result.patient_id != patient_id:
            raise HTTPException(status_code=404, detail="unknown result for patient")
    else:
        result = repo.latest_result(session, patient_id)
        if result is None:
            raise HTTPException(status_code=409, detail="patient has no results")

    run = repo.create_run(session, patient_id, result.id)
    session.commit()  # make the run row durable before the background task reads it

    bus.create(run.run_id)
    task = asyncio.create_task(
        execute_run(
            bus=bus,
            session_factory=session_factory,
            runner_factory=runner_factory,
            run_id=run.run_id,
            patient_id=patient_id,
            result_id=result.id,
        )
    )
    tasks.add(task)
    task.add_done_callback(tasks.discard)
    return RunStarted(run_id=run.run_id)


@router.get("/runs/{run_id}")
def get_run(run_id: str, session: SessionDep) -> RunSummary:
    """Return the run summary or 404."""
    run = repo.get_run(session, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="unknown run")
    return run


@router.get("/runs/{run_id}/events")
def run_events(run_id: str, session: SessionDep, bus: BusDep) -> StreamingResponse:
    """Stream the run's agent trace as SSE (live channel, else replay from persisted steps)."""
    if bus.has(run_id):
        return StreamingResponse(stream_live(bus, run_id), media_type="text/event-stream")
    if repo.get_run(session, run_id) is None:
        raise HTTPException(status_code=404, detail="unknown run")
    return StreamingResponse(stream_persisted(session, run_id), media_type="text/event-stream")
