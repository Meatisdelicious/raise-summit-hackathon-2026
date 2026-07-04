"""Helpers for driving runs and parsing the SSE agent trace in tests."""

from __future__ import annotations

import json

from httpx import AsyncClient


def parse_sse_frames(body: str) -> list[dict[str, object]]:
    """Split an SSE body on blank lines, strip the ``data: `` prefix, and JSON-decode each frame."""
    frames: list[dict[str, object]] = []
    for chunk in body.split("\n\n"):
        chunk = chunk.strip()
        if not chunk:
            continue
        assert chunk.startswith("data: "), f"bad SSE frame: {chunk!r}"
        payload = chunk[len("data: ") :]
        parsed = json.loads(payload)
        assert isinstance(parsed, dict)
        frames.append(parsed)
    return frames


async def stream_run_events(client: AsyncClient, run_id: str) -> list[dict[str, object]]:
    """GET the SSE trace for ``run_id`` and return the parsed frames in order.

    The stream ends when the run closes (after its brief/run are committed), so on return the run
    is fully persisted.
    """
    resp = await client.get(f"/api/runs/{run_id}/events")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    return parse_sse_frames(resp.text)


async def drive_run_to_completion(client: AsyncClient, patient_id: str) -> str:
    """Start a run for ``patient_id``, consume its SSE stream to completion, return the run id."""
    started = await client.post(f"/api/patients/{patient_id}/runs", json={})
    assert started.status_code == 200
    run_id = started.json()["run_id"]
    assert isinstance(run_id, str) and run_id
    await stream_run_events(client, run_id)
    return run_id
