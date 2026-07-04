"""Tolerant extraction of a single JSON object from an LLM response.

Live models (Kimi K2) often wrap the object in markdown fences or surrounding prose, so we also try
the substring from the first ``{`` to the last ``}``. Deterministic replay/stub outputs are already
pure JSON and parse on the first try, so cassette behaviour is unchanged.
"""

from __future__ import annotations

import json


def extract_json_object(content: str | None) -> dict[str, object] | None:
    """Return the first JSON object in ``content`` (fenced/prose wrapping tolerated), else None."""
    if not content:
        return None
    text = content.strip()
    candidates = [text]
    start = text.find("{")
    end = text.rfind("}")
    if 0 <= start < end:
        candidates.append(text[start : end + 1])
    for candidate in candidates:
        try:
            data: object = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data
    return None
