# Safety, privacy & compliance

Condensed from [`docs/doc.md`](doc.md) §12, §19, §20. **Binding on every build-agent.**

## Privacy — the hard rule
- **Public repo + hosted demo contain synthetic data only.** No real report is sent to Vultr or any
  external model.
- No real identifier, clinician name, organization, logo, dossier number, or original-report metadata
  in commits, issues, screenshots, logs, prompts, or presentation material.
- Real/original material lives only under `data/private/` (git-ignored; must be empty in the public
  tree). The Phase-0 gate (`make privacy` / `/privacy-gate`) hard-blocks the build until the tree is
  verified clean.
- Health data is sensitive personal data; pseudonymization does not make it anonymous.

## Synthetic-generation rules (spec §12.2)
Fictional names/addresses/orgs/IDs/clinicians · all dates and numeric values changed · no copied
logos/branding/dossier numbers/exact layouts · cleared PDF metadata · every page watermarked
`SYNTHETIC DATA — NOT FOR CLINICAL USE` · deterministic generator seed · generator + templates in the
repo · documents under `data/synthetic/` · a manifest mapping each document to its ground truth · do
not train a model on any real source report.

## Product safety
- Explicit clinician-authored recommendation required — the agent never decides that a result *needs*
  follow-up on its own.
- Deterministic hard validation before any closure; the LLM can never override a validator.
- Human review on ambiguity; human approval before any external action.
- No diagnosis, interpretation, treatment, clinical-risk score, or guideline adjudication.
- Complete audit trail; **fail open to review** — uncertainty keeps the loop visible, never silently
  closed. **False closure = 0.**

## Security baseline (spec §20)
Private object-storage bucket · TLS everywhere · server-side secrets only · least-privilege creds ·
separate dev/demo creds · authenticated approval endpoint · short-lived signed document URLs · file
type/size/checksum validation · no executable uploads · dependency + secret scanning in CI · structured
audit events without full document text · synthetic-only backups · credential rotation after the event.

## Not production
The hackathon must not claim production compliance, clinical efficacy, or HDS eligibility. A real
deployment would require a formal legal, privacy, security, clinical-safety, and procurement
assessment. This spec is an engineering boundary, not legal or medical advice.
