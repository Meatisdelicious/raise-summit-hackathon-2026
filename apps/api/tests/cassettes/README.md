# Replay cassettes (Lane D)

Hand-authored, synthetic, deterministic responses so `CS_INFERENCE_MODE=replay` can run the full
agent loop **offline** — no Vultr calls in CI. `data/synthetic/manifest.json` is the ground truth each
case's content is consistent with.

## How the replay clients find a cassette

The inference lane keys cassettes by a **sha256 of the canonical request** — see
`cyclesentinel/inference/cassette.py` (`llm_request_key(messages, tools, model)` /
`retriever_request_key(query, rule_type, top_k, model)`; temperature is pinned to 0 and uuids/
timestamps are scrubbed). At run time `get_llm_client` / `get_visual_retriever` read from
`CS_CASSETTE_DIR/<client>/<key>.json`, where `CS_CASSETTE_DIR` is pointed at one case dir:

```
apps/api/tests/cassettes/<CASE>/llm/<sha256>.json         # a ChatResponse
apps/api/tests/cassettes/<CASE>/retriever/<sha256>.json   # a list[RetrievalHit]  (BARE array)
```

Run one case with `CS_CASSETTE_DIR=apps/api/tests/cassettes/<CASE> CS_INFERENCE_MODE=replay`.

## What is committed here (authored content) vs the sha256 files

The **sha256 filename depends on the exact request** the agent/tools lanes send, which isn't frozen
yet. So this dir commits the stable, reviewable **authored content** under semantic names:

- `llm/01_plan.json`, `llm/02_brief.json` — `ChatResponse` payloads (`{"content": "...", "tool_calls": []}`).
  `content` is a JSON string: `{"plan": [...]}` for the plan turn; `{"interpretation": "...",
  "recommended_action": "..."}` for the brief turn. Decision states, citations and escalation level are
  set by the **deterministic** agent (calculators + `manifest.json`), never parsed out of the prose.
- `retriever/<rule_type>.json` — a **bare JSON array** of `RetrievalHit`. Each hit's `text` is
  byte-identical to the matching `data/synthetic/corpus/<doc>/page-NN.txt` layer, with `article`,
  `page`, `doc_id`, `rule_type`, and a synthetic `score` (higher = better; hits are pre-sorted).

To materialize the sha256-keyed files the replay clients actually read, run **offline**:

```
cd apps/api && uv run python ../../scripts/record_cassettes.py --seed
```

That re-keys the authored content via the real `llm_request_key` / `retriever_request_key`. Live
recording (`--live`, needs Vultr keys) overwrites them from real responses. Both are governed by
`build_request_specs()` in `scripts/record_cassettes.py` — **the single point to keep in sync with the
agent lane's requests.** The generated `<sha256>.json` files are not committed (they change when the
agent's prompts change); re-run `--seed` after the agent freezes its prompts.

## Per-case turn sequence

| Case | LLM turns | Retriever branches |
|------|-----------|--------------------|
| **K** | `01_plan`, `02_brief` | `ohss`, `luteinization` (dual flag, urgent) |
| **R** | `01_plan`, `02_brief` | **none** — the control proving retrieval is computation-driven |
| **P** | `01_plan`, `02_brief` | `poor_responder` (info) |
| **M** | `01_plan`, `02_brief` | **none** (missing timepoint is detected, not retrieved) |

The empty `R/retriever/` and `M/retriever/` dirs carry a `.gitkeep` so the "no conditional retrieval"
control stays visible.
