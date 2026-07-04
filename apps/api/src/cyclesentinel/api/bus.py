"""In-process, per-run pub/sub for the SSE agent trace.

One :class:`EventBus` lives on ``app.state`` for the whole process. A run gets a channel
(:meth:`EventBus.create`) before its background task starts; the task publishes each
:data:`~cyclesentinel.events.AgentEvent` to it. A channel keeps an append-only ``log`` so a late
subscriber (or a second viewer) replays the whole trace from the start, then follows live events
until the run closes. This is deliberately in-memory: the demo runs in a single process, and a
finished run can also be re-streamed from the persisted steps (``api.runner.reconstruct_events``).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from cyclesentinel.events import AgentEvent

# ``None`` is the close sentinel pushed onto every subscriber queue when a run finishes.
_Queue = asyncio.Queue["AgentEvent | None"]


@dataclass
class _Channel:
    """One run's event log plus the set of live subscriber queues."""

    log: list[AgentEvent] = field(default_factory=list)
    subscribers: set[_Queue] = field(default_factory=set)
    closed: bool = False


class EventBus:
    """Per-run event fan-out with replay of already-emitted events."""

    def __init__(self) -> None:
        self._channels: dict[str, _Channel] = {}

    def create(self, run_id: str) -> None:
        """Open a channel for ``run_id`` (idempotent) so subscribers can attach immediately."""
        self._channels.setdefault(run_id, _Channel())

    def has(self, run_id: str) -> bool:
        """Return whether a live/buffered channel exists for ``run_id``."""
        return run_id in self._channels

    def publish(self, run_id: str, event: AgentEvent) -> None:
        """Append ``event`` to the run's log and hand it to every current subscriber."""
        channel = self._channels.setdefault(run_id, _Channel())
        channel.log.append(event)
        for queue in channel.subscribers:
            queue.put_nowait(event)

    def close(self, run_id: str) -> None:
        """Mark the run finished and wake every subscriber so its stream can end."""
        channel = self._channels.setdefault(run_id, _Channel())
        channel.closed = True
        for queue in channel.subscribers:
            queue.put_nowait(None)

    def drop(self, run_id: str) -> None:
        """Forget a run's channel (used by ``demo/reset``)."""
        self._channels.pop(run_id, None)

    def clear(self) -> None:
        """Forget every channel."""
        self._channels.clear()

    async def subscribe(self, run_id: str) -> AsyncIterator[AgentEvent]:
        """Yield the run's buffered events, then live ones, until the run closes.

        The buffered snapshot and the subscriber registration happen with no ``await`` between
        them, so on a single-threaded event loop no publish can slip through the gap.
        """
        channel = self._channels.setdefault(run_id, _Channel())
        queue: _Queue = asyncio.Queue()
        backlog = list(channel.log)
        already_closed = channel.closed
        channel.subscribers.add(queue)
        try:
            for event in backlog:
                yield event
            if already_closed:
                return
            while True:
                item = await queue.get()
                if item is None:
                    return
                yield item
        finally:
            channel.subscribers.discard(queue)
