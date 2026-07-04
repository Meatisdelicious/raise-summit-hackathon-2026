#!/usr/bin/env python3
"""Ownership guard (AGENTS.md §4, docs/WORKTREES.md).

Fails if the current branch's diff (vs the merge-base with main) touches any path outside the task's
declared `owned_paths` in tasks/<TASK>.md. This is what makes parallel worktree agents safe.

Usage: python scripts/check_ownership.py T12   [--base main]
"""
from __future__ import annotations

import argparse
import fnmatch
import subprocess
import sys
from pathlib import Path

# Files every task is implicitly allowed to touch (its own spec + PR metadata).
ALWAYS_ALLOWED = ("tasks/{task}.md",)


def parse_owned_paths(task: str) -> list[str]:
    spec = Path("tasks") / f"{task}.md"
    if not spec.exists():
        print(f"error: {spec} not found", file=sys.stderr)
        raise SystemExit(2)
    lines = spec.read_text(encoding="utf-8").splitlines()
    # Read the YAML frontmatter between the first two '---' fences.
    if not lines or lines[0].strip() != "---":
        print(f"error: {spec} has no frontmatter", file=sys.stderr)
        raise SystemExit(2)
    end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    fm = lines[1:end]
    owned: list[str] = []
    in_owned = False
    for ln in fm:
        if ln.startswith("owned_paths:"):
            in_owned = True
            continue
        if in_owned:
            stripped = ln.strip()
            if stripped.startswith("- "):
                owned.append(stripped[2:].strip())
            elif stripped and not ln.startswith((" ", "\t")):
                break  # next top-level key
    return owned


def matches(path: str, pattern: str) -> bool:
    # Directory-prefix pattern (ends with '/') matches everything under it.
    if pattern.endswith("/"):
        return path == pattern.rstrip("/") or path.startswith(pattern)
    # '**' glob — normalize to fnmatch semantics.
    if fnmatch.fnmatch(path, pattern):
        return True
    # Treat a bare dir pattern without trailing slash as a prefix too.
    if "*" not in pattern and (path == pattern or path.startswith(pattern + "/")):
        return True
    return False


def changed_files(base: str) -> list[str]:
    try:
        mb = subprocess.run(["git", "merge-base", "HEAD", base], capture_output=True, text=True, check=True).stdout.strip()
    except subprocess.CalledProcessError:
        mb = base
    out = subprocess.run(["git", "diff", "--name-only", f"{mb}...HEAD"], capture_output=True, text=True, check=True).stdout
    return [f for f in out.splitlines() if f]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("task")
    ap.add_argument("--base", default="main")
    args = ap.parse_args()

    owned = parse_owned_paths(args.task) + [p.format(task=args.task) for p in ALWAYS_ALLOWED]
    files = changed_files(args.base)
    if not files:
        print(f"ownership[{args.task}]: no changed files vs {args.base}")
        return 0

    violations = [f for f in files if not any(matches(f, p) for p in owned)]
    if violations:
        print(f"OWNERSHIP GUARD FAILED for {args.task} — diff touches paths outside owned_paths:", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        print("\nowned_paths:", file=sys.stderr)
        for p in owned:
            print(f"  · {p}", file=sys.stderr)
        print("\nStay within your lane or escalate for an integration task (AGENTS.md §12).", file=sys.stderr)
        return 1

    print(f"✅ ownership[{args.task}]: all {len(files)} changed files are within owned_paths.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
