"""REST endpoint shape + behavior tests (every endpoint hit at least once)."""

from __future__ import annotations

from httpx import AsyncClient

from tests.api.sse_util import drive_run_to_completion


async def test_health_and_ready(client: AsyncClient) -> None:
    health = await client.get("/api/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}

    ready = await client.get("/api/ready")
    assert ready.status_code == 200
    assert ready.json() == {"ready": True}


async def test_list_patients(client: AsyncClient) -> None:
    resp = await client.get("/api/patients")
    assert resp.status_code == 200
    patients = resp.json()
    ids = {p["id"] for p in patients}
    assert {"pat-K", "pat-R", "pat-P", "pat-M"} <= ids
    sample = next(p for p in patients if p["id"] == "pat-K")
    assert set(sample) == {
        "id",
        "label",
        "protocol",
        "cycle_day",
        "amh",
        "antral_follicle_count",
        "pcos_flag",
    }
    assert sample["protocol"] == "antagonist"
    assert sample["pcos_flag"] is True


async def test_get_patient_and_404(client: AsyncClient) -> None:
    ok = await client.get("/api/patients/pat-K")
    assert ok.status_code == 200
    assert ok.json()["label"] == "Patient K"

    missing = await client.get("/api/patients/pat-NOPE")
    assert missing.status_code == 404


async def test_patient_results_trajectory(client: AsyncClient) -> None:
    resp = await client.get("/api/patients/pat-K/results")
    assert resp.status_code == 200
    results = resp.json()
    assert [r["cycle_day"] for r in results] == [3, 5, 7, 8]
    assert set(results[0]) >= {"id", "patient_id", "cycle_day", "drawn_at", "e2", "lh"}

    assert (await client.get("/api/patients/pat-NOPE/results")).status_code == 404


async def test_latest_brief_null_then_present(client: AsyncClient) -> None:
    before = await client.get("/api/patients/pat-K/latest-brief")
    assert before.status_code == 200
    assert before.json() is None

    await drive_run_to_completion(client, "pat-K")

    after = await client.get("/api/patients/pat-K/latest-brief")
    assert after.status_code == 200
    brief = after.json()
    assert brief is not None
    assert brief["patient_id"] == "pat-K"
    assert "OHSS_RISK_ESCALATE" in brief["states"]


async def test_run_summary(client: AsyncClient) -> None:
    run_id = await drive_run_to_completion(client, "pat-K")
    resp = await client.get(f"/api/runs/{run_id}")
    assert resp.status_code == 200
    summary = resp.json()
    assert summary["run_id"] == run_id
    assert summary["patient_id"] == "pat-K"
    assert summary["finished_at"] is not None
    assert summary["brief_id"] == "brief-K"
    assert summary["step_count"] == 15  # one persisted step per emitted event
    assert summary["final_states"] == [
        "OHSS_RISK_ESCALATE",
        "PREMATURE_LUTEINIZATION_FLAG",
    ]

    assert (await client.get("/api/runs/nope")).status_code == 404


async def test_start_run_unknown_patient_and_result(client: AsyncClient) -> None:
    assert (await client.post("/api/patients/pat-NOPE/runs", json={})).status_code == 404
    bad_result = await client.post("/api/patients/pat-K/runs", json={"result_id": "res-NOPE"})
    assert bad_result.status_code == 404


async def test_validate_and_reject_brief(client: AsyncClient) -> None:
    await drive_run_to_completion(client, "pat-K")

    validated = await client.post(
        "/api/briefs/brief-K/validate",
        json={"validated_by": "dr_smith", "edits": {"recommended_action": "Coast 24h."}},
    )
    assert validated.status_code == 200
    body = validated.json()
    assert body["validated_by"] == "dr_smith"
    assert body["validated_at"] is not None
    assert body["recommended_action"] == "Coast 24h."

    rejected = await client.post(
        "/api/briefs/brief-K/reject",
        json={"validated_by": "dr_jones", "reason": "needs manual review"},
    )
    assert rejected.status_code == 200
    assert "AMBIGUOUS_REQUIRES_REVIEW" in rejected.json()["states"]

    assert (
        await client.post("/api/briefs/nope/validate", json={"validated_by": "x"})
    ).status_code == 404


async def test_demo_reset(client: AsyncClient) -> None:
    await drive_run_to_completion(client, "pat-K")
    assert (await client.get("/api/patients/pat-K/latest-brief")).json() is not None

    reset = await client.post("/api/demo/reset")
    assert reset.status_code == 200
    assert reset.json() == {"ok": True}

    # briefs/runs wiped, patients reseeded
    assert (await client.get("/api/patients/pat-K/latest-brief")).json() is None
    assert (await client.get("/api/patients")).status_code == 200
