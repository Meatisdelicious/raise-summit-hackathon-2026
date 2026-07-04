"""SSE agent-trace tests: golden K order, the routine-R no-branch invariant, and replay."""

from __future__ import annotations

from httpx import AsyncClient

from tests.api.scripted import GOLDEN_K_TYPES, GOLDEN_R_TYPES
from tests.api.sse_util import parse_sse_frames, stream_run_events


async def test_killer_k_golden_sequence(client: AsyncClient) -> None:
    started = await client.post("/api/patients/pat-K/runs", json={})
    run_id = started.json()["run_id"]

    frames = await stream_run_events(client, run_id)
    types = [f["type"] for f in frames]

    assert types == list(GOLDEN_K_TYPES)
    assert types[0] == "plan"
    assert types[-1] == "done"
    # the money shot: each branch is immediately followed by a retrieve_rule
    branch_positions = [i for i, t in enumerate(types) if t == "branch"]
    assert branch_positions, "killer case must branch"
    for i in branch_positions:
        assert types[i + 1] == "retrieve_rule"
    # every retrieve_rule frame carries a citation resolving to a page
    for frame in frames:
        if frame["type"] == "retrieve_rule":
            citation = frame["citation"]
            assert isinstance(citation, dict)
            assert citation["page"] >= 1
            assert citation["quote"]
    # run id stamped on every framed event
    for frame in frames:
        if "run_id" in frame:
            assert frame["run_id"] == run_id


async def test_routine_r_invariant_no_conditional_retrieval(client: AsyncClient) -> None:
    started = await client.post("/api/patients/pat-R/runs", json={})
    run_id = started.json()["run_id"]

    frames = await stream_run_events(client, run_id)
    types = [f["type"] for f in frames]

    assert types == list(GOLDEN_R_TYPES)
    assert "branch" not in types
    assert "retrieve_rule" not in types
    assert "compute" in types  # it still computes — retrievals are computation-driven
    assert types[0] == "plan"
    assert types[-1] == "done"


async def test_finished_run_replays_same_sequence(client: AsyncClient) -> None:
    started = await client.post("/api/patients/pat-K/runs", json={})
    run_id = started.json()["run_id"]

    first = [f["type"] for f in await stream_run_events(client, run_id)]
    # second read of a finished run must be byte-deterministic (buffered replay in step order)
    second = [f["type"] for f in await stream_run_events(client, run_id)]
    assert first == second == list(GOLDEN_K_TYPES)


async def test_events_unknown_run_404(client: AsyncClient) -> None:
    resp = await client.get("/api/runs/does-not-exist/events")
    assert resp.status_code == 404


async def test_sse_framing_is_compact_single_line(client: AsyncClient) -> None:
    started = await client.post("/api/patients/pat-K/runs", json={})
    run_id = started.json()["run_id"]
    resp = await client.get(f"/api/runs/{run_id}/events")
    body = resp.text
    # exact "data: <json>\n\n" framing; no pretty-printed multiline JSON payloads
    for chunk in body.split("\n\n"):
        if chunk.strip():
            assert chunk.startswith("data: ")
            assert "\n" not in chunk  # single-line compact JSON per frame
    assert parse_sse_frames(body)  # parses cleanly
