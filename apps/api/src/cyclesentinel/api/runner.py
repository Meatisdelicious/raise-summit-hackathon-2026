"""Background execution of an agent run and deterministic replay of a finished one.

:func:`execute_run` is the bridge between the agent-loop lane (which only *yields* events) and the
API's responsibilities: fan events out on the :class:`EventBus`, persist each as an ordered step
(the full event JSON in ``result_summary`` powers replay/audit), save the brief, and close the run.
:func:`reconstruct_events` rebuilds the exact ordered trace from those persisted steps so a run can
be re-streamed after its in-memory channel is gone.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from cyclesentinel.api.bus import EventBus
from cyclesentinel.api.deps import RunnerFactory
from cyclesentinel.db.models import StepRow
from cyclesentinel.db.repo import append_step, finish_run, save_brief
from cyclesentinel.events import (
    AgentEvent,
    BriefEvent,
    DoneEvent,
    ErrorEvent,
    agent_event_adapter,
    sse_format,
)


async def execute_run(
    *,
    bus: EventBus,
    session_factory: sessionmaker[Session],
    runner_factory: RunnerFactory,
    run_id: str,
    patient_id: str,
    result_id: str,
) -> None:
    """Drive one run to completion: publish + persist every event, then close the channel."""
    session = session_factory()
    final_states: list[str] = []
    brief_id: str | None = None
    try:
        runner = runner_factory(session)
        async for event in runner.run(run_id, patient_id, result_id):
            bus.publish(run_id, event)
            append_step(
                session,
                run_id,
                tool=event.type,
                result_summary=agent_event_adapter.dump_json(event).decode("utf-8"),
            )
            if isinstance(event, BriefEvent):
                brief_id = save_brief(session, event.brief).id
            elif isinstance(event, DoneEvent):
                final_states = [str(state) for state in event.final_states]
        finish_run(session, run_id, final_states, brief_id)
        session.commit()
    except Exception as exc:  # noqa: BLE001 - surface any runner failure as a trace error frame
        session.rollback()
        bus.publish(run_id, ErrorEvent(run_id=run_id, message=str(exc)))
        try:
            finish_run(session, run_id, ["AMBIGUOUS_REQUIRES_REVIEW"], brief_id)
            session.commit()
        except Exception:  # noqa: BLE001 - never let cleanup mask the original failure
            session.rollback()
    finally:
        bus.close(run_id)
        session.close()


def reconstruct_events(session: Session, run_id: str) -> list[AgentEvent]:
    """Rebuild a finished run's ordered event trace from its persisted steps."""
    rows = session.scalars(
        select(StepRow).where(StepRow.run_id == run_id).order_by(StepRow.step)
    ).all()
    return [agent_event_adapter.validate_json(row.result_summary) for row in rows]


async def stream_persisted(session: Session, run_id: str) -> AsyncIterator[bytes]:
    """Yield SSE frames for a finished run reconstructed from persisted steps."""
    for event in reconstruct_events(session, run_id):
        yield sse_format(event)


async def stream_live(bus: EventBus, run_id: str) -> AsyncIterator[bytes]:
    """Yield SSE frames for a run from its (buffered + live) bus channel."""
    async for event in bus.subscribe(run_id):
        yield sse_format(event)
