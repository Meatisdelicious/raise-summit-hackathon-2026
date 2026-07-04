"""Cassette storage + deterministic request keying for the replay inference mode.

A *cassette* is a directory of recorded responses keyed by a hash of the *canonical* request, so a
logically identical request always resolves to the same file regardless of run-specific noise
(``run_id``, uuids, timestamps). The key rule (:func:`cassette_key`):

1. force ``temperature`` to ``0`` (we only ever call at temperature 0);
2. drop volatile keys anywhere in the structure (:data:`VOLATILE_KEYS`);
3. replace uuid-shaped and ISO-8601-timestamp-shaped string *values* with stable placeholders;
4. ``sha256`` of the compact, sorted-key JSON of the result.

Layout on disk::

    tests/cassettes/<CASE>/llm/<key>.json         # one recorded ChatResponse (as JSON)
    tests/cassettes/<CASE>/retriever/<key>.json   # one recorded list[RetrievalHit] (as JSON)

The Tools and Data lanes record cassettes by building the same request dicts via
:func:`llm_request_key` / :func:`retriever_request_key` and saving the response payload with
:meth:`Cassette.save`. Replay clients only ever read — a miss raises, never hits the network.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from cyclesentinel.enums import RuleType
from cyclesentinel.inference.base import ChatMessage, ToolSchema

# Field names whose values are per-run noise and must never influence a cassette key.
VOLATILE_KEYS: frozenset[str] = frozenset(
    {
        "run_id",
        "id",
        "tool_call_id",
        "created",
        "created_at",
        "started_at",
        "finished_at",
        "validated_at",
        "drawn_at",
        "timestamp",
        "time",
        "latency_ms",
    }
)

_UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
_ISO_TS_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


def _scrub(value: object) -> object:
    """Recursively drop volatile keys and neutralize uuid/timestamp-shaped string values."""
    if isinstance(value, Mapping):
        return {k: _scrub(v) for k, v in value.items() if k not in VOLATILE_KEYS}
    if isinstance(value, (list, tuple)):
        return [_scrub(v) for v in value]
    if isinstance(value, str):
        if _UUID_RE.search(value):
            return "<uuid>"
        if _ISO_TS_RE.search(value):
            return "<ts>"
        return value
    return value


def cassette_key(request: Mapping[str, object]) -> str:
    """Return the stable ``sha256`` key for a request (temperature pinned, noise scrubbed)."""
    canonical: dict[str, object] = dict(request)
    canonical["temperature"] = 0  # pinned: every call is temperature 0
    scrubbed = _scrub(canonical)
    blob = json.dumps(scrubbed, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def llm_request_key(
    messages: Sequence[ChatMessage], tools: Sequence[ToolSchema] | None, model: str
) -> str:
    """Key an LLM chat request from its messages, tool schemas, and model id."""
    request: dict[str, object] = {
        "kind": "llm",
        "model": model,
        "messages": [m.to_wire() for m in messages],
        "tools": [t.to_wire() for t in tools] if tools else [],
    }
    return cassette_key(request)


def retriever_request_key(query: str, rule_type: RuleType, top_k: int, model: str) -> str:
    """Key a retrieval request from its query, rule-type filter, ``top_k``, and model id."""
    request: dict[str, object] = {
        "kind": "retriever",
        "model": model,
        "query": query,
        "rule_type": str(rule_type),
        "top_k": top_k,
    }
    return cassette_key(request)


@dataclass(frozen=True)
class Cassette:
    """A cassette directory (e.g. ``tests/cassettes/<CASE>/llm``); ``save`` writes under ``root``.

    ``extra_roots`` lets replay resolve a key across sibling per-case directories without pinning
    ``CS_CASSETTE_DIR`` to one case: ``load`` tries ``root`` first, then each extra root in order.
    Keys are unique content hashes, so a single ``make dev`` server can serve all demo cases at once
    (the routine and killer patients produce different requests → different keys → no collision).
    """

    root: Path
    extra_roots: tuple[Path, ...] = ()

    def path_for(self, key: str) -> Path:
        """Absolute path of the JSON file holding the response for ``key`` under ``root``."""
        return self.root / f"{key}.json"

    def load(self, key: str) -> object | None:
        """Return the recorded payload for ``key`` (searching ``root`` then ``extra_roots``)."""
        for base in (self.root, *self.extra_roots):
            path = base / f"{key}.json"
            if path.exists():
                data: object = json.loads(path.read_text(encoding="utf-8"))
                return data
        return None

    def save(self, key: str, payload: object) -> None:
        """Write ``payload`` (already JSON-serializable) as the recorded response for ``key``."""
        self.root.mkdir(parents=True, exist_ok=True)
        text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
        self.path_for(key).write_text(text + "\n", encoding="utf-8")
