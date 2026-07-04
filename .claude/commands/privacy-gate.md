---
description: Phase-0 privacy hard gate — verify no real PHI / original PDFs are anywhere in the tree. Blocks the build.
---

You are running the **Phase-0 privacy gate**. Nothing else in the build may start until this passes.
(See `AGENTS.md` §1 and `docs/safety.md`.)

## Steps
1. Run the scanner: `make privacy` (which runs `python scripts/privacy_scan.py` + gitleaks if
   available).
2. The scanner must confirm ALL of:
   - No `*.PDF` / original-report files anywhere except under `data/synthetic/`.
   - `data/private/` is empty (or absent) in the tracked tree; it is git-ignored.
   - No obvious real identifiers (names, dates of birth, national IDs, dossier numbers, org/lab names,
     access identifiers) in tracked files, per the scanner's patterns.
   - No secrets committed (gitleaks / the env patterns).
3. Also verify `git ls-files` contains no file under `data/private/` and no `*.PDF`.

## Result
- **PASS** → report "Privacy gate PASSED — build may proceed" and exit 0.
- **FAIL** → list every hit (file + reason), report "Privacy gate FAILED — build is BLOCKED", and do
  **not** allow any build task to start. The originals must be moved out of the tree (to
  `data/private/` or outside the repo) and any leaked identifiers removed before re-running.

This gate is intentionally strict: a privacy leak risks disqualification.
