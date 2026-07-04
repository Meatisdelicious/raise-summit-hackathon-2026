#!/usr/bin/env python3
"""Record / seed replay cassettes against the inference lane's real key rule (Lane D, manual-run).

Cassettes are looked up by a sha256 of the *canonical request* — see
``cyclesentinel.inference.cassette`` (:func:`llm_request_key`, :func:`retriever_request_key`). This
script owns the mapping from each demo case to the exact requests, so the recorded/seeded files land
under the sha256 filenames the replay clients (``ReplayLLMClient`` / ``ReplayRetriever``) read:

    apps/api/tests/cassettes/<CASE>/llm/<key>.json         # a ChatResponse
    apps/api/tests/cassettes/<CASE>/retriever/<key>.json   # a list[RetrievalHit]

Two modes:

- ``--live``  : call the live Vultr clients and save their real responses (needs
  ``CS_INFERENCE_MODE=live`` + credentials). CI never runs this.
- ``--seed``  : offline. Re-key the HAND-AUTHORED content files (``01_plan.json`` / ``02_brief.json`` /
  ``<rule_type>.json``, produced by Lane D) to their sha256 filenames — no network. This materializes
  the deterministic replay set for tests.

Run from the backend env, e.g.::

    cd apps/api && CS_INFERENCE_MODE=live uv run python ../../scripts/record_cassettes.py --live
    cd apps/api && uv run python ../../scripts/record_cassettes.py --seed

> ALIGNMENT: :func:`build_request_specs` must mirror the requests the AGENT lane actually sends
> (LLM messages/tools per turn; retriever query/rule_type/top_k per branch). It is the single point to
> keep in sync — once the agent freezes its prompts, update it here and re-run to refresh keys.
"""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SYNTH = REPO_ROOT / "data" / "synthetic"
CASSETTES = REPO_ROOT / "apps" / "api" / "tests" / "cassettes"

# Which conditional branches each case takes, in order (mirrors manifest.retrieve_rule_branches).
CASE_BRANCHES: dict[str, list[str]] = {
    "K": ["ohss", "luteinization"],
    "R": [],
    "P": ["poor_responder"],
    "M": [],
}
# Ordered LLM turns per case and the authored content file that backs each.
LLM_TURNS: list[str] = ["01_plan", "02_brief"]


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _trajectory_query(patient: dict[str, Any], results: list[dict[str, Any]]) -> str:
    """A compact query string from the trajectory (retriever + LLM share this framing).

    ALIGNED with the agent lane (``cyclesentinel.agent.prompts.run_query``): patient baseline +
    E2 series only — deliberately no manifest summary, so the agent can reproduce it at runtime.
    """
    series = ", ".join(f"d{r['cycle_day']}={r['e2']}pg/mL" for r in results if r["e2"] is not None)
    return (
        f"{patient['label']} ({patient['protocol']}, cycle day {patient['cycle_day']}, "
        f"PCOS={patient['pcos_flag']}). E2 trajectory: {series}."
    )


@dataclass
class CaseSpec:
    """The ordered requests for one case (mirror of what the agent sends)."""

    case: str
    query: str
    branches: list[str] = field(default_factory=list)  # rule_type per retriever turn


def build_request_specs() -> list[CaseSpec]:
    """Build per-case request specs from the synthetic data. ALIGN with the agent lane."""
    patients = {p["id"]: p for p in _load_json(SYNTH / "patients.json")}
    by_patient: dict[str, list[dict[str, Any]]] = {}
    for r in _load_json(SYNTH / "results.json"):
        by_patient.setdefault(r["patient_id"], []).append(r)
    manifest = _load_json(SYNTH / "manifest.json")

    specs: list[CaseSpec] = []
    for case_name, case in manifest["cases"].items():
        patient = patients[case["patient_id"]]
        results = sorted(by_patient[patient["id"]], key=lambda r: r["cycle_day"])
        specs.append(
            CaseSpec(
                case=case_name,
                query=_trajectory_query(patient, results),
                branches=CASE_BRANCHES[case_name],
            )
        )
    return specs


# --- imports from the inference lane (guarded so the tool fails loudly, never silently) ----------
def _import_inference() -> Any:
    try:
        from cyclesentinel.agent.prompts import brief_messages, plan_messages
        from cyclesentinel.config import get_settings
        from cyclesentinel.enums import RuleType
        from cyclesentinel.inference import (
            Cassette,
            get_llm_client,
            get_visual_retriever,
            llm_request_key,
            retriever_request_key,
        )

        # Aligned with LLM_TURNS: the exact messages the agent lane sends per turn (system + user),
        # so cassette keys are built from prompts.py — the single source of truth (never duplicated).
        message_builders = [plan_messages, brief_messages]
        return {
            "get_settings": get_settings,
            "Cassette": Cassette,
            "get_llm_client": get_llm_client,
            "get_visual_retriever": get_visual_retriever,
            "llm_request_key": llm_request_key,
            "retriever_request_key": retriever_request_key,
            "message_builders": message_builders,
            "RuleType": RuleType,
        }
    except Exception as exc:  # noqa: BLE001 — manual tool: surface wiring gaps plainly.
        print(
            f"record_cassettes: cannot import the inference lane API ({exc}). "
            "Run inside the backend env: cd apps/api && uv run python ../../scripts/record_cassettes.py",
            file=sys.stderr,
        )
        raise SystemExit(3) from exc


async def _record_live(api: dict[str, Any]) -> int:
    settings = api["get_settings"]()
    if settings.inference_mode != "live":
        print("record_cassettes --live: set CS_INFERENCE_MODE=live first.", file=sys.stderr)
        return 2

    llm = api["get_llm_client"](settings)
    retriever = api["get_visual_retriever"](settings)
    builders = api["message_builders"]
    for spec in build_request_specs():
        llm_dir = CASSETTES / spec.case / "llm"
        for turn, build in zip(LLM_TURNS, builders, strict=True):
            messages = build(spec.query)
            resp = await llm.chat(messages)
            # Save both the human-inspectable content file and the sha256-keyed file for this env.
            api["Cassette"](llm_dir).save(f"{turn}", resp.model_dump())  # writes <turn>.json
            key = api["llm_request_key"](messages, None, settings.cs_llm_model)
            api["Cassette"](llm_dir).save(key, resp.model_dump())
        for rule_type in spec.branches:
            rt = api["RuleType"](rule_type)
            key = api["retriever_request_key"](spec.query, rt, 2, settings.cs_retriever_model)
            hits = await retriever.retrieve(spec.query, rt, 2)
            api["Cassette"](CASSETTES / spec.case / "retriever").save(
                key, [h.model_dump() for h in hits]
            )
        print(f"recorded {spec.case}: llm={len(LLM_TURNS)}, retriever={len(spec.branches)}")
    return 0


def _seed_offline(api: dict[str, Any]) -> int:
    """Re-key the hand-authored content files to their sha256 filenames (no network)."""
    settings = api["get_settings"]()
    builders = api["message_builders"]
    for spec in build_request_specs():
        llm_dir = CASSETTES / spec.case / "llm"
        for turn, build in zip(LLM_TURNS, builders, strict=True):
            src = llm_dir / f"{turn}.json"
            if not src.exists():
                print(f"seed: missing authored content {src}", file=sys.stderr)
                return 4
            key = api["llm_request_key"](build(spec.query), None, settings.cs_llm_model)
            api["Cassette"](llm_dir).save(key, _load_json(src))
        ret_dir = CASSETTES / spec.case / "retriever"
        for rule_type in spec.branches:
            src = ret_dir / f"{rule_type}.json"
            if not src.exists():
                print(f"seed: missing authored content {src}", file=sys.stderr)
                return 4
            rt = api["RuleType"](rule_type)
            key = api["retriever_request_key"](spec.query, rt, 2, settings.cs_retriever_model)
            api["Cassette"](ret_dir).save(key, _load_json(src))
        print(f"seeded {spec.case}: llm={len(LLM_TURNS)}, retriever={len(spec.branches)}")
    return 0


def main(argv: list[str]) -> int:
    mode = argv[1] if len(argv) > 1 else ""
    if mode not in {"--live", "--seed"}:
        print("usage: record_cassettes.py [--live | --seed]", file=sys.stderr)
        return 2
    api = _import_inference()
    if mode == "--live":
        return asyncio.run(_record_live(api))
    return _seed_offline(api)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
