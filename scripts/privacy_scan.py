#!/usr/bin/env python3
"""Phase-0 privacy gate (AGENTS.md §1, docs/safety.md).

Scans the TRACKED git tree for signs of real health data / secrets. Exits non-zero on any hit so it
can hard-block the build in CI and locally (`make privacy`). Synthetic demo material under
data/synthetic/ is the only allowed PDF location.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

# Directories/paths where committed PDFs and generated docs are allowed.
ALLOWED_DOC_PREFIXES = ("data/synthetic/",)

# Files we never scan for identifier patterns (docs about privacy naturally mention these words).
SKIP_CONTENT_SCAN = {
    ".gitignore", ".gitleaks.toml",
    "docs/safety.md", "docs/doc.md", "docs/PRD.md", "AGENTS.md", "CLAUDE.md", "README.md",
    "scripts/privacy_scan.py",
}
SKIP_CONTENT_DIRS = ("tasks/", "docs/", ".claude/", ".github/")

# Binary/text extensions to content-scan.
TEXT_EXTS = {".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".txt", ".md", ".csv", ".sql", ".env", ".yaml", ".yml"}

# Heuristic identifier patterns. Tuned to catch obvious real-PHI leaks, not to be a DLP product.
IDENTIFIER_PATTERNS = {
    "french_ssn_nir": re.compile(r"\b[12]\s?\d{2}\s?\d{2}\s?\d{2,3}\s?\d{3}\s?\d{2,3}\b"),
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@(?!example\.(?:com|org)|synthetic\.)[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "dob_label": re.compile(r"(?i)\b(date of birth|né[e]? le|born on|patient dob)\b"),
    "long_digit_id": re.compile(r"\b\d{11,}\b"),
}

SECRET_PATTERNS = {
    "aws_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "generic_secret": re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][^'\"]{12,}['\"]"),
}


def tracked_files() -> list[str]:
    out = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True).stdout
    return [line for line in out.splitlines() if line]


def main() -> int:
    hits: list[str] = []
    files = tracked_files()

    for f in files:
        low = f.lower()
        # 1) No original/real PDFs anywhere except data/synthetic/.
        if low.endswith(".pdf"):
            if not any(f.startswith(p) for p in ALLOWED_DOC_PREFIXES):
                hits.append(f"[PDF outside data/synthetic/] {f}")
        # 2) Nothing tracked under data/private/.
        if f.startswith("data/private/") and not f.endswith(".gitkeep"):
            hits.append(f"[tracked file under data/private/] {f}")

    # 3) Content scan for identifiers/secrets on text files (excluding docs/specs).
    for f in files:
        if f in SKIP_CONTENT_SCAN or f.startswith(SKIP_CONTENT_DIRS):
            continue
        if Path(f).suffix.lower() not in TEXT_EXTS:
            continue
        try:
            text = Path(f).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for name, pat in {**IDENTIFIER_PATTERNS, **SECRET_PATTERNS}.items():
            if pat.search(text):
                hits.append(f"[{name}] {f}")

    if hits:
        print("PRIVACY GATE FAILED — build is BLOCKED. Hits:", file=sys.stderr)
        for h in sorted(set(hits)):
            print(f"  - {h}", file=sys.stderr)
        print("\nMove originals to data/private/ (ignored) or outside the repo, and remove any "
              "leaked identifiers/secrets. See docs/safety.md.", file=sys.stderr)
        return 1

    print("✅ Privacy gate PASSED — no real PHI / original PDFs / secrets found in the tracked tree.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
