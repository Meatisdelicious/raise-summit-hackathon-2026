# Safety, privacy & boundary

Binding on everyone working in this repo.

## Product boundary — why this is not a "medical advice bot"
- **Enterprise user = the lab biologist + the PMA clinician. Never the patient.** Cycle Sentinel is
  internal triage / professional clinical-decision-support, exactly like a clinical-trial-matching tool.
- **A human validates before anything reaches the clinic or patient.** The agent drafts a brief and an
  escalation flag; the biologist approves/edits/rejects. No output is auto-sent.
- **No autonomous clinical verdict.** The LLM interprets and writes prose; **deterministic calculators +
  rules decide the escalation flag**. The agent does not diagnose, prescribe, choose a dose, or apply a
  guideline on its own — it surfaces the cited rule for a human to act on.
- **Everything is grounded.** Every clause of a brief resolves to a numbered **protocol/SOP article**. No
  ungrounded recommendation ships.
- **Fail safe.** Missing/ambiguous data → `MISSING_TIMEPOINT` / `AMBIGUOUS_REQUIRES_REVIEW`, never a
  silent "normal." Anything that should escalate must never resolve to `ROUTINE_CONTINUE`.

## Privacy — synthetic only (hard rule)
- Serial hormone results tied to a patient are **Article-9 sensitive personal data**. The public repo and
  the hosted demo use **synthetic data only**. No real result, identifier, or original PDF/report anywhere
  — repo, Vultr, prompts, logs, screenshots, or the demo.
- Real/original material lives only under `data/private/` (git-ignored; empty in the tracked tree). The
  privacy gate (`make privacy` / `scripts/privacy_scan.py`) hard-blocks commits that would leak it, and
  runs as a required CI job.
- Synthetic generation: fictional patients, changed dates/values, cleared metadata, a deterministic seed,
  the generator + templates in the repo, a manifest mapping each case to its ground truth.

> ⚠️ A real-PHI leak already occurred once in this repo's history (lab PDFs under
> `docs/healthcare_data/`). Treat the privacy gate as non-optional. Never commit real lab documents.

## Sovereignty (Vultr / HDS)
Host the agent, the LLM (**Kimi K2 Instruct**), the visual retriever (**Vultron Prime-8B**), and the
protocol/SOP page embeddings (**Vultr Vector Store**) all in an **EU region**, **HDS-aligned** — the
sovereign alternative to sensitive fertility data leaving the EU. Synthetic hormone data + protocol
pages never leave Vultr EU; no third-party model is called. The hackathon must not claim production HDS
certification or clinical efficacy; this is an engineering boundary, not legal or medical advice.

## Security baseline
Private object-storage bucket · TLS everywhere · server-side secrets only · authenticated validation/
escalation endpoint · audit trail of runs, tools, decisions, and human validations · dependency + secret
scanning in CI · synthetic-only data.
