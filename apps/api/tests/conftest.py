"""Shared pytest fixtures for the cyclesentinel test suite.

Minimal placeholder — later build phases extend this with app/client/db fixtures.
Tests default to the offline ``replay`` inference mode.
"""

from __future__ import annotations

import os

os.environ.setdefault("CS_INFERENCE_MODE", "replay")
