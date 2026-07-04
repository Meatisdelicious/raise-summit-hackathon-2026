"""FastAPI dependencies and the agent-runner seam.

Request-scoped dependencies pull the process singletons off ``app.state`` (session factory, event
bus, background-task set, runner factory) and hand out a committing DB session.

The **agent runner** is owned by the parallel agent-loop lane. This module only depends on the
:class:`AgentRunner` protocol (an object whose ``run`` yields :data:`AgentEvent` frames) and on a
:class:`RunnerFactory` that builds one bound to a DB session. :func:`make_runner_factory` loads the
real builder dynamically (``cyclesentinel.agent.loop.build_agent_runner``) when it exists and
falls back to a :class:`DegradedRunner` so the API stays serviceable before that lane lands.

Expected builder contract (the agent-loop lane must expose this so live/demo runs work):

    def build_agent_runner(
        *, session: Session, settings: Settings,
        llm: LLMClient, retriever: VisualRetriever,
    ) -> AgentRunner: ...
"""

from __future__ import annotations

import asyncio
import importlib
from collections.abc import AsyncIterator, Iterator
from typing import Annotated, Protocol, cast, runtime_checkable

from fastapi import Depends, Request
from sqlalchemy.orm import Session, sessionmaker

from cyclesentinel.api.bus import EventBus
from cyclesentinel.config import Settings, get_settings
from cyclesentinel.enums import DecisionState
from cyclesentinel.events import AgentEvent, DoneEvent, ErrorEvent
from cyclesentinel.inference import (
    LLMClient,
    VisualRetriever,
    get_llm_client,
    get_visual_retriever,
)


@runtime_checkable
class AgentRunner(Protocol):
    """Drives one agent run, yielding the ordered trace as :data:`AgentEvent` frames."""

    def run(self, run_id: str, patient_id: str, result_id: str) -> AsyncIterator[AgentEvent]:
        """Yield the run's events in order, ending with a ``done`` (or ``error``) frame."""
        ...


class RunnerFactory(Protocol):
    """Builds an :class:`AgentRunner` bound to a specific DB session."""

    def __call__(self, session: Session) -> AgentRunner: ...


class RunnerBuilder(Protocol):
    """The construction entrypoint the agent-loop lane exposes as ``build_agent_runner``."""

    def __call__(
        self,
        *,
        session: Session,
        settings: Settings,
        llm: LLMClient,
        retriever: VisualRetriever,
    ) -> AgentRunner: ...


class DegradedRunner:
    """Fallback runner used until the agent-loop lane is wired: emits a clear error, then done.

    Keeps ``POST /runs`` + SSE functional (and honestly non-silent) before ``build_agent_runner``
    exists, per the fail-safe rule that nothing unresolved may look ``ROUTINE_CONTINUE``.
    """

    async def run(self, run_id: str, patient_id: str, result_id: str) -> AsyncIterator[AgentEvent]:
        yield ErrorEvent(
            run_id=run_id,
            message="agent loop not wired: cyclesentinel.agent.loop.build_agent_runner is missing",
        )
        yield DoneEvent(run_id=run_id, final_states=[DecisionState.AMBIGUOUS_REQUIRES_REVIEW])


def _load_real_builder() -> RunnerBuilder | None:
    """Return the agent-loop lane's ``build_agent_runner`` if importable, else ``None``."""
    try:
        module = importlib.import_module("cyclesentinel.agent.loop")
    except ModuleNotFoundError:
        return None
    builder = getattr(module, "build_agent_runner", None)
    if builder is None:
        return None
    return cast(RunnerBuilder, builder)


def make_runner_factory(settings: Settings) -> RunnerFactory:
    """Build the process runner factory: real agent loop when available, else degraded."""
    builder = _load_real_builder()

    def factory(session: Session) -> AgentRunner:
        if builder is not None:
            return builder(
                session=session,
                settings=settings,
                llm=get_llm_client(settings),
                retriever=get_visual_retriever(settings),
            )
        return DegradedRunner()

    return factory


# --- request-scoped dependencies ---------------------------------------------------------------


def get_db(request: Request) -> Iterator[Session]:
    """Yield a session from the app's factory; commit on success, roll back on error."""
    factory = cast("sessionmaker[Session]", request.app.state.session_factory)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session_factory(request: Request) -> sessionmaker[Session]:
    """Return the process session factory (for background runs that own their own session)."""
    return cast("sessionmaker[Session]", request.app.state.session_factory)


def get_bus(request: Request) -> EventBus:
    """Return the process event bus."""
    return cast(EventBus, request.app.state.bus)


def get_tasks(request: Request) -> set[asyncio.Task[None]]:
    """Return the set that keeps background run tasks alive."""
    return cast("set[asyncio.Task[None]]", request.app.state.tasks)


def get_runner_factory(request: Request) -> RunnerFactory:
    """Return the process runner factory."""
    return cast(RunnerFactory, request.app.state.runner_factory)


SettingsDep = Annotated[Settings, Depends(get_settings)]
SessionDep = Annotated[Session, Depends(get_db)]
SessionFactoryDep = Annotated["sessionmaker[Session]", Depends(get_session_factory)]
BusDep = Annotated[EventBus, Depends(get_bus)]
TasksDep = Annotated["set[asyncio.Task[None]]", Depends(get_tasks)]
RunnerDep = Annotated[RunnerFactory, Depends(get_runner_factory)]
