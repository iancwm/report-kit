"""The REVIEW step's record, ``build/review.json`` (spec §4.8).

The record expands the composition brief's manual checks over rendered pages
and keeps the visual-review claim separate from the checklist itself.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping

from .diagnostics import make_diagnostic
from .target import TargetState

REVIEW_SCHEMA_VERSION = "1.0.0"
REVIEW_PATH = Path("build") / "review.json"
VISUAL_REVIEW_STATES = ("done", "unavailable")


def _review_path(pdf: Path, state: TargetState) -> Path:
    root = state.source_root if state.source_root is not None else Path(pdf).resolve().parent
    return root / REVIEW_PATH


def _manual_review_items(state: TargetState) -> list[str]:
    """Read the brief's review items, falling back to the target registry.

    The fallback keeps review useful for a project whose brief has not yet
    copied the registry defaults. A present, explicitly empty list remains
    empty because it is an author decision.
    """
    if state.source_root is None:
        return []
    try:
        from .composition_audit import ROLE_REGISTRIES, find_brief

        brief_path = find_brief(state.source_root, state)
        registry = ROLE_REGISTRIES.get(state.publication_type)
        default_items = list(registry.manual_review) if registry is not None else []
        if brief_path is None:
            return default_items
        brief = json.loads(brief_path.read_text(encoding="utf-8"))
        if not isinstance(brief, dict):
            return default_items
        items = brief.get("manual_review", default_items)
        if not isinstance(items, list) or any(not isinstance(item, str) for item in items):
            return default_items
        return items
    except (OSError, ValueError, json.JSONDecodeError):
        return []


def _rendered_page_count(pdf: Path, state: TargetState) -> int | None:
    """Return the rendered page count when a manifest or PDF reader is available."""
    if state.source_root is not None:
        manifest_root = Path(state.source_root) / "build"
        try:
            manifests = list(manifest_root.glob("**/pages.json"))
        except OSError:
            manifests = []
        matching: list[tuple[float, int]] = []
        for path in manifests:
            try:
                manifest = json.loads(path.read_text(encoding="utf-8"))
                page_count = manifest.get("page_count") if isinstance(manifest, dict) else None
                manifest_pdf = manifest.get("pdf") if isinstance(manifest, dict) else None
                if (
                    isinstance(page_count, int) and not isinstance(page_count, bool) and page_count > 0
                    and isinstance(manifest_pdf, str) and Path(manifest_pdf).name == Path(pdf).name
                ):
                    matching.append((path.stat().st_mtime, page_count))
            except (OSError, ValueError, json.JSONDecodeError):
                continue
        if matching:
            return max(matching, key=lambda item: item[0])[1]

    # PyMuPDF is an optional rendering dependency. Review must still be
    # recordable when it is absent (that is one reason visual_review may be
    # "unavailable"), so a missing reader simply leaves page unspecified.
    try:
        import fitz  # type: ignore[import-not-found]

        document = fitz.open(str(pdf))
        try:
            return len(document) or None
        finally:
            document.close()
    except Exception:
        return None


def write_review(pdf: Path, state: TargetState, visual_review: str | None) -> dict[str, Any]:
    """Write and return ``build/review.json`` for ``pdf``."""
    if visual_review not in (*VISUAL_REVIEW_STATES, None):
        raise ValueError(f"visual_review must be one of {VISUAL_REVIEW_STATES!r} or None")
    items = _manual_review_items(state)
    page_count = _rendered_page_count(Path(pdf), state)
    pages: list[int | None] = list(range(1, page_count + 1)) if page_count is not None else [None]
    checklist = [
        {"page": page, "item": item, "done": visual_review == "done"}
        for page in pages
        for item in items
    ]
    record: dict[str, Any] = {
        "schema_version": REVIEW_SCHEMA_VERSION,
        "pdf": str(pdf),
        "publication_type": state.publication_type,
        "theme": state.theme,
        "visual_review": visual_review,
        "checklist": checklist,
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
    ``RK_INTENT_MISMATCH``. Older build selections without ``source_mode`` are
    compared on publication type and theme only.
    """
    intent = state.intent
    if not isinstance(intent, Mapping):
        return None, []

    expected: dict[str, Any] = {}
    actual: dict[str, Any] = {}
    mismatches: list[str] = []
    for key in ("publication_type", "theme"):
        if key not in intent:
            continue
        # ``theme`` is the canonical, rendered theme in the build report;
        # ``requested_theme`` preserves aliases such as book/technical.
        selected_key = "requested_theme" if key == "theme" and selection.get("requested_theme") is not None else key
        expected[key] = intent.get(key)
        actual[key] = selection.get(selected_key)
        if actual[key] != expected[key]:
            mismatches.append(key)

    if "source_mode" in intent and "source_mode" in selection:
        expected["source_mode"] = intent.get("source_mode")
        actual["source_mode"] = selection.get("source_mode")
        if actual["source_mode"] != expected["source_mode"]:
            mismatches.append("source_mode")

    if not expected:
        return None, []
    if not mismatches:
        return True, []

    def target_label(values: Mapping[str, Any]) -> str:
        type_value = values.get("publication_type", "unknown")
        theme_value = values.get("theme", "unknown")
        mode_value = f" source={values['source_mode']}" if "source_mode" in values else ""
        return f"structure={type_value} look={theme_value}{mode_value}"

    diagnostic = make_diagnostic(
        "target_contract",
        f"Built target {target_label(actual)} differs from locked intent {target_label(expected)}.",
        code="RK_INTENT_MISMATCH",
        details={"expected": expected, "actual": actual, "mismatched_fields": mismatches},
    )
    return False, [diagnostic]
