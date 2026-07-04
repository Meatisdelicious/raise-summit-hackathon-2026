"""End-to-end test over the REAL agent loop, driven through the FastAPI app in replay mode.

This exercises the true production path — ``create_app()`` started via its lifespan over a seeded
in-memory SQLite, with ``CS_INFERENCE_MODE=replay``, and WITHOUT overriding
``app.state.runner_factory``. The run is therefore driven by
``make_runner_factory`` -> ``cyclesentinel.agent.loop.build_agent_runner`` -> the real
:class:`AgentRunner` (persistence owned by ``execute_run``), not the scripted API-lane runner.

It is the regression guard for the wiring gaps: on the pre-fix code the missing
``build_agent_runner`` forced the :class:`DegradedRunner`, so every case emitted ``error`` ->
``AMBIGUOUS_REQUIRES_REVIEW``; this test's golden-sequence assertions fail there and pass once the
seams are wired. Each case sets ``CS_CASSETTE_DIR`` to its recorded cassette folder (as the agent
lane does) so replay is hermetic.
"""

from __future__ import annotations

import os

os.environ["CS_INFERENCE_MODE"] = "replay"
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"

from collections.abc import AsyncIterator  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from cyclesentinel.config import get_settings  # noqa: E402
from cyclesentinel.main import create_app  # noqa: E402
from tests.agent.conftest import CASE_IDS  # noqa: E402
from tests.api.sse_util import parse_sse_frames  # noqa: E402

_CASSETTES = Path(__file__).resolve().parents[1] / "cassettes"

_COMPUTE = ["compute"] * 6  # e2_rate, e2_per_follicle, ohss_composite, progesterone, response, gap

# The exact ordered event `type`s the real loop emits per case (first "plan", last "done").
GOLDEN_TYPES: dict[str, list[str]] = {
    "K": [
        "plan",
        "retrieve",
        "retrieve",
        *_COMPUTE,
        "branch",
        "retrieve_rule",
        "branch",
        "retrieve_rule",
        "action",
        "brief",
        "escalate",
        "done",
    ],
    "R": ["plan", "retrieve", "retrieve", *_COMPUTE, "action", "brief", "done"],
    "P": [
        "plan",
        "retrieve",
        "retrieve",
        *_COMPUTE,
        "branch",
        "retrieve_rule",
        "action",
        "brief",
        "escalate",
        "done",
    ],
    "M": ["plan", "retrieve", "retrieve", *_COMPUTE, "action", "brief", "escalate", "done"],
}

EXPECTED_STATES: dict[str, list[str]] = {
    "K": ["OHSS_RISK_ESCALATE", "PREMATURE_LUTEINIZATION_FLAG"],
    "R": ["ROUTINE_CONTINUE"],
    "P": ["POOR_RESPONSE_FLAG"],
    "M": ["MISSING_TIMEPOINT"],
}


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """A client over a freshly started, seeded app that uses the REAL runner factory."""
    get_settings.cache_clear()
    app = create_app()
    async with app.router.lifespan_context(app):
        # Deliberately NOT setting app.state.runner_factory: this drives build_agent_runner.
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as http_client:
            yield http_client


async def _run_case(client: AsyncClient, case: str) -> list[dict[str, object]]:
    """Point replay at the case cassette, start a run, stream its SSE trace to completion."""
    os.environ["CS_CASSETTE_DIR"] = str(_CASSETTES / case)
    patient_id, _result_id = CASE_IDS[case]
    started = await client.post(f"/api/patients/{patient_id}/runs", json={})
    assert started.status_code == 200, started.text
    run_id = started.json()["run_id"]

    resp = await client.get(f"/api/runs/{run_id}/events")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    frames = parse_sse_frames(resp.text)
    for frame in frames:
        if "run_id" in frame:
            assert frame["run_id"] == run_id
    return frames


@pytest.mark.parametrize("case", ["K", "R", "P", "M"])
async def test_real_path_golden_sequence_and_states(client: AsyncClient, case: str) -> None:
    frames = await _run_case(client, case)
    types = [f["type"] for f in frames]

    # No error frame from the DegradedRunner — the real loop ran end to end.
    assert "error" not in types, f"{case}: real loop should not emit an error frame"
    assert types == GOLDEN_TYPES[case]
    assert types[0] == "plan"
    assert types[-1] == "done"

    done = frames[-1]
    assert done["type"] == "done"
    assert done["final_states"] == EXPECTED_STATES[case]


async def test_killer_k_branches_pair_with_retrievals(client: AsyncClient) -> None:
    """K is the money shot: exactly two branch -> retrieve_rule pairs, dual escalating state."""
    frames = await _run_case(client, "K")
    types = [f["type"] for f in frames]

    assert types.count("branch") == 2
    assert types.count("retrieve_rule") == 2
    branch_positions = [i for i, t in enumerate(types) if t == "branch"]
    for i in branch_positions:
        assert types[i + 1] == "retrieve_rule"

    rule_types = [f["rule_type"] for f in frames if f["type"] == "retrieve_rule"]
    assert rule_types == ["ohss", "luteinization"]
    assert frames[-1]["final_states"] == ["OHSS_RISK_ESCALATE", "PREMATURE_LUTEINIZATION_FLAG"]


async def test_finished_real_run_replays_from_persisted_steps(client: AsyncClient) -> None:
    """A second read hits reconstruct_events: execute_run is the sole persister."""
    os.environ["CS_CASSETTE_DIR"] = str(_CASSETTES / "K")
    started = await client.post("/api/patients/pat-K/runs", json={})
    run_id = started.json()["run_id"]

    live = [
        f["type"] for f in parse_sse_frames((await client.get(f"/api/runs/{run_id}/events")).text)
    ]
    # Second read of a finished run rebuilds the trace from persisted step rows (full event JSON).
    replayed = [
        f["type"] for f in parse_sse_frames((await client.get(f"/api/runs/{run_id}/events")).text)
    ]
    assert live == replayed == GOLDEN_TYPES["K"]


async def test_routine_r_is_the_not_rag_invariant(client: AsyncClient) -> None:
    """R computes but performs ZERO conditional retrieval — the agent-not-RAG invariant."""
    frames = await _run_case(client, "R")
    types = [f["type"] for f in frames]

    assert "branch" not in types
    assert "retrieve_rule" not in types
    assert "escalate" not in types
    assert "compute" in types
    assert frames[-1]["final_states"] == ["ROUTINE_CONTINUE"]


async def test_latest_brief_grounds_and_validates(client: AsyncClient) -> None:
    """K's brief grounds to real citations and a biologist can validate it in place."""
    await _run_case(client, "K")

    brief_resp = await client.get("/api/patients/pat-K/latest-brief")
    assert brief_resp.status_code == 200
    brief = brief_resp.json()
    assert brief is not None
    brief_id = brief["id"]

    citations = brief["citations"]
    assert citations, "K's escalating brief must cite protocol/SOP articles (hard rule 3)"
    for citation in citations:
        assert citation["page"] >= 1
        assert citation["article"]
        assert citation["quote"]

    validated = await client.post(
        f"/api/briefs/{brief_id}/validate", json={"validated_by": "dr-bio"}
    )
    assert validated.status_code == 200
    assert validated.json()["validated_by"] == "dr-bio"


async def test_multiple_patients_keep_distinct_persisted_briefs(client: AsyncClient) -> None:
    """Run all four cases in one DB: each patient must retain its own brief (no id collision).

    Regression guard for the deterministic-id collision — a per-run ``IdFactory`` reset made every
    brief ``brief-0001``, so ``save_brief`` overwrote a single global row and every previously-run
    patient's ``latest-brief`` came back null. The run is namespaced so ids stay unique across runs.
    """
    for case in ("K", "R", "P", "M"):
        await _run_case(client, case)

    brief_ids: dict[str, str] = {}
    for case in ("K", "R", "P", "M"):
        patient_id, _ = CASE_IDS[case]
        brief = (await client.get(f"/api/patients/{patient_id}/latest-brief")).json()
        assert brief is not None, f"{patient_id} lost its brief after later runs"
        assert brief["patient_id"] == patient_id
        brief_ids[patient_id] = brief["id"]

    assert len(set(brief_ids.values())) == 4, f"brief ids collided: {brief_ids}"
