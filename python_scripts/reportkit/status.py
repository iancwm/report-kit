"""Re-hydrate the loop from disk alone (spec §4.8).

``reportkit status`` reports the target, the intent, the brief's status, the
last successful step, open diagnostics, ``visual_review``, and ``next_step``.
It reads only the consumer project, so an agent that lost its context can
recover with one command.

Wave 0 stub: returns the target payload and ``next_step``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .loop import next_step, target_payload
from .target import load_target

STATUS_SCHEMA_VERSION = "1.0.0"


def collect_status(source_root: Path) -> dict[str, Any]:
    """Return the status payload for ``source_root`` (no envelope fields)."""
    state = load_target(source_root)
    return {
        "target": target_payload(state),
        "intent": state.intent,
        "next_step": next_step("status", state, {"passed": True, "diagnostics": []}),
    }
