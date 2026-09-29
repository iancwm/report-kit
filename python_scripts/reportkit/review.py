"""The REVIEW step's record, ``build/review.json`` (spec §4.8).

It holds a per-page checklist from the brief's manual-review items and an
honest ``visual_review: done | unavailable``; ``status`` prints a delivery
caveat when the host could not view rendered pages.

Wave 0 stub: writes a minimal record; intent comparison always passes.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping

from .target import TargetState

REVIEW_SCHEMA_VERSION = "1.0.0"
REVIEW_PATH = Path("build") / "review.json"
VISUAL_REVIEW_STATES = ("done", "unavailable")


def _review_path(pdf: Path, state: TargetState) -> Path:
    root = state.source_root if state.source_root is not None else Path(pdf).resolve().parent
    return root / REVIEW_PATH


def write_review(pdf: Path, state: TargetState, visual_review: str | None) -> dict[str, Any]:
    """Write and return ``build/review.json`` for ``pdf``."""
    record: dict[str, Any] = {
        "schema_version": REVIEW_SCHEMA_VERSION,
        "pdf": str(pdf),
        "publication_type": state.publication_type,
        "theme": state.theme,
        "visual_review": visual_review,
        "checklist": [],
        "reviewed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    path = _review_path(pdf, state)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record


def read_review(source_root: Path) -> dict[str, Any] | None:
    """Return the project's ``build/review.json`` or ``None``."""
    path = Path(source_root) / REVIEW_PATH
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def compare_intent(selection: Mapping[str, Any], state: TargetState) -> tuple[bool | None, list[dict[str, Any]]]:
    """Compare a build-report ``selection`` with ``state.intent``.

    Returns ``(matches_intent, diagnostics)``; a mismatch yields
    ``RK_INTENT_MISMATCH``. Stub: ``(None, [])``.
    """
    return None, []
