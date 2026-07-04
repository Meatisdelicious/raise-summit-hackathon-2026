#!/usr/bin/env python3
"""Index the synthetic protocol/SOP corpus into the Vultr Vector Store (live-mode setup).

The real Vultr Vector Store API (confirmed against ``/v1/vector_store``) has **no per-item metadata
and no server-side filter**: an item is just ``{content}`` and search returns ``{id, content}`` with
no score. So we use **one collection per ``rule_type``** — ``<prefix>-<rule_type>`` — which gives the
agent's conditional retrieval its filtering for free (the branch queries exactly one collection), and
we recover each hit's citation (``doc_id`` / ``page`` / ``article``) by matching the returned content
back to the local corpus at query time (see ``retrieval/vultr_store.py``). ``rule_type`` is known
from *which* collection was queried.

Run (needs the live key in the environment)::

    VULTR_INFERENCE_API_KEY=... cd apps/api && uv run python ../../scripts/index_corpus.py

Idempotent: each run deletes and recreates the per-rule_type collections, then re-uploads every
non-cover page. Uploads the page **text layer** (what the text-only LLM cites); Vultr embeds it.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import httpx


def _sleep_backoff(attempt: int) -> None:
    """Short capped backoff between retries (a fresh collection settles within a second or two)."""
    time.sleep(min(0.5 * (attempt + 1), 2.0))

# Import the shared corpus loader + collection-id helper from the backend package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api" / "src"))
from cyclesentinel.enums import RuleType  # noqa: E402
from cyclesentinel.retrieval.collections import collection_id  # noqa: E402
from cyclesentinel.retrieval.corpus import CorpusPage, load_corpus  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[1]
_CORPUS_DIR = _REPO_ROOT / "data" / "synthetic" / "corpus"
_TIMEOUT = httpx.Timeout(60.0, connect=15.0)


def main() -> int:
    api_key = os.environ.get("VULTR_INFERENCE_API_KEY", "").strip()
    if not api_key:
        print("error: set VULTR_INFERENCE_API_KEY in the environment", file=sys.stderr)
        return 2
    base = os.environ.get("VULTR_INFERENCE_BASE_URL", "https://api.vultrinference.com/v1").rstrip("/")
    prefix = os.environ.get("VULTR_VECTOR_COLLECTION", "cs").strip() or "cs"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    corpus = load_corpus(_CORPUS_DIR)
    # Group non-cover pages by rule_type (cover pages are letterhead, not citable rules).
    by_rule: dict[RuleType, list[CorpusPage]] = {}
    for page in corpus.pages:
        if page.article.strip().lower() == "cover":
            continue
        by_rule.setdefault(page.rule_type, []).append(page)

    with httpx.Client(timeout=_TIMEOUT, headers=headers) as client:
        for rule_type, pages in by_rule.items():
            name = collection_id(prefix, rule_type)  # short, alphanumeric id == what Vultr stores
            # Clean reindex: delete (ignore 404) then recreate.
            client.delete(f"{base}/vector_store/{name}")
            created = client.post(f"{base}/vector_store", json={"name": name})
            created.raise_for_status()
            returned_id = created.json().get("collection", {}).get("id", name)
            if returned_id != name:  # guard against Vultr re-deriving a different id
                print(f"warning: requested id {name!r} but Vultr stored {returned_id!r}")
            for page in pages:
                # A freshly created collection is briefly not-yet-queryable (eventual consistency):
                # retry the item POST a few times on the 422 "Collection not found".
                for attempt in range(6):
                    resp = client.post(
                        f"{base}/vector_store/{name}/items", json={"content": page.text}
                    )
                    if resp.status_code != 422 or attempt == 5:
                        resp.raise_for_status()
                        break
                    _sleep_backoff(attempt)
            print(f"indexed {len(pages):>2} pages -> collection '{name}' ({rule_type})")

    print(f"\ndone: set VULTR_VECTOR_COLLECTION={prefix} and VECTOR_STORE=vultr in .env")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
