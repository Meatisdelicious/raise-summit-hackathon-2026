---
description: Refresh replay cassettes by recording real Vultr Serverless Inference responses for cases A–H. Needs credentials.
---

You are refreshing the **replay cassettes** so CI validates the same behavior the live demo produces.
This requires **live Vultr credentials** and is a human-supervised task (see task `T32`).

## Preconditions
- `.env` has `VULTR_INFERENCE_API_KEY`, `VULTR_INFERENCE_BASE_URL`, `VULTR_MODEL` set.
- The synthetic corpus + manifest exist (`data/synthetic/`, `data/manifests/ground_truth.json`).
- The agent orchestrator (T30) and API (T31) exist.

## Steps
1. `export LOOPCLOSER_INFERENCE_MODE=live` and confirm connectivity with a tiny probe.
2. Run `make record` — this uses `RecordingInferenceClient` to run the full agent over cases A–H and
   write request→response cassettes to `apps/api/tests/cassettes/`.
3. Switch back to replay: `export LOOPCLOSER_INFERENCE_MODE=replay` and run `make eval` — confirm the
   release gates still pass deterministically against the freshly recorded cassettes.
4. Commit the updated cassettes (they are the ONLY committed artifact of this task; check no secrets or
   real data leaked into them — cassettes contain synthetic prompts/responses only).
5. Open a PR labeled `task:T32` per the normal protocol. Note in the PR body that cassettes were
   re-recorded from live Vultr on the synthetic corpus.

## Guardrails
- Never record against anything but synthetic data.
- Never commit credentials. Verify cassettes contain no secrets.
- Temperature stays 0 so replay is deterministic.
