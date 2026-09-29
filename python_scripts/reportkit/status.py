"""Re-hydrate the loop from disk alone (spec §4.8).

``reportkit status`` reports the target, the intent, the brief's status, the
last successful step, open diagnostics, ``visual_review``, and ``next_step``.
It reads only the consumer project, so an agent that lost its context can
recover with one command.

Wave 0 stub: returns the target payload and ``next_step``.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from .composition_audit import audit_source, find_brief
from .config import CONFIG_NAME, load_publication_config, resolve_output
from .diagnostics import make_diagnostic
from .loop import next_step, target_payload
from .review import REVIEW_PATH, read_review
from .target import INTENT_PATH, load_target, target_gate

STATUS_SCHEMA_VERSION = "1.0.0"


def collect_status(source_root: Path) -> dict[str, Any]:
    """Reconstruct a status payload using the consumer project's disk state."""
    root = Path(source_root).resolve()
    state = load_target(root)
    diagnostics: list[dict[str, Any]] = list(target_gate(state))
    intent = _read_intent(root, diagnostics)
    output_root = _output_root(root, diagnostics)
    reports = _load_build_reports(output_root, diagnostics)

    latest_report: dict[str, Any] | None = None
    if reports:
        latest_report = max(reports, key=lambda item: _mtime(item[0]))[1]
        diagnostics.extend(_report_diagnostics(latest_report))
        selection = latest_report.get("selection")
        if isinstance(selection, dict) and selection.get("matches_intent") is False:
            diagnostics.append(make_diagnostic(
                "target_contract",
                "The latest build target does not match the saved publication intent.",
                code="RK_INTENT_MISMATCH",
            ))

    brief_path = _brief_path(root, state, intent)
    source_path = _audit_source_path(root, state, output_root)
    brief_status: dict[str, Any] = {"path": _display_path(root, brief_path), "passed": None}
    if brief_path is not None:
        try:
            audit = audit_source(source_path or root / state.main, brief_path, state)
            audit_diagnostics = audit.get("diagnostics", [])
            if isinstance(audit_diagnostics, list):
                diagnostics.extend(item for item in audit_diagnostics if isinstance(item, dict))
            brief_status["passed"] = bool(audit.get("passed"))
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
            diagnostics.append(make_diagnostic(
                "publication_validation", f"Could not audit the composition brief: {exc}",
                code="RK_STATUS_AUDIT", source={"file": _display_path(root, brief_path)},
            ))
            brief_status["passed"] = False

    review = read_review(root)
    visual_review = review.get("visual_review") if isinstance(review, dict) else None
    if visual_review not in {"done", "unavailable"}:
        visual_review = None
    delivery_caveat = None
    if visual_review == "unavailable":
        delivery_caveat = (
            "Visual review was unavailable. State this in the delivery message and do not claim the rendered pages were visually reviewed."
        )

    last_step = _last_successful_step(root, output_root, reports, review)
    passed = not any(item.get("severity") == "error" for item in diagnostics)
    result = {
        "target": target_payload(state),
        "intent": intent,
        "brief": brief_status,
        "last_step": last_step,
        "diagnostics": _unique_diagnostics(diagnostics),
        "visual_review": visual_review,
        "delivery_caveat": delivery_caveat,
    }
    result["next_step"] = next_step("status", state, {"passed": passed, "diagnostics": result["diagnostics"]})
    return result


def _read_intent(root: Path, diagnostics: list[dict[str, Any]]) -> dict[str, Any] | None:
    path = root / INTENT_PATH
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        diagnostics.append(make_diagnostic(
            "configuration_error", f"Could not read the saved publication intent: {exc}",
            code="RK_STATUS_INTENT", source={"file": _display_path(root, path)},
        ))
        return None
    if not isinstance(value, dict):
        diagnostics.append(make_diagnostic(
            "configuration_error", "The saved publication intent must be a JSON object.",
            code="RK_STATUS_INTENT", source={"file": _display_path(root, path)},
        ))
        return None
    return value


def _output_root(root: Path, diagnostics: list[dict[str, Any]]) -> Path:
    try:
        config = load_publication_config(root / CONFIG_NAME)
        configured = resolve_output(config, root)
    except (OSError, ValueError) as exc:
        diagnostics.append(make_diagnostic(
            "configuration_error", f"Could not resolve the publication output directory: {exc}",
            code="RK_STATUS_OUTPUT", source={"file": CONFIG_NAME},
        ))
        configured = None
    return configured or root / "build"


def _load_build_reports(output_root: Path, diagnostics: list[dict[str, Any]]) -> list[tuple[Path, dict[str, Any]]]:
    candidates = {output_root / "build-report.json", *output_root.glob("**/build-report.json")}
    reports: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(candidates):
        if not path.is_file():
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            diagnostics.append(make_diagnostic(
                "configuration_error", f"Could not read build report: {exc}",
                code="RK_STATUS_BUILD_REPORT", source={"file": str(path)},
            ))
            continue
        if isinstance(value, dict):
            reports.append((path, value))
        else:
            diagnostics.append(make_diagnostic(
                "configuration_error", "Build report must be a JSON object.",
                code="RK_STATUS_BUILD_REPORT", source={"file": str(path)},
            ))
    return reports


def _report_diagnostics(report: dict[str, Any]) -> list[dict[str, Any]]:
    value: Any = report.get("diagnostics", [])
    if isinstance(value, dict):
        value = value.get("diagnostics", value.get("issues", []))
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _brief_path(root: Path, state: Any, intent: dict[str, Any] | None) -> Path | None:
    try:
        discovered = find_brief(root, state)
    except (OSError, ValueError):
        discovered = None
    candidates: list[Path] = []
    configured = intent.get("composition_brief") if intent else None
    if isinstance(configured, str) and configured.strip():
        candidates.append(Path(configured))
    if discovered is not None:
        candidates.append(Path(discovered))
    candidates.extend((Path("composition-brief.json"), Path("editorial-brief.json")))
    for candidate in candidates:
        path = candidate if candidate.is_absolute() else root / candidate
        try:
            resolved = path.resolve()
            resolved.relative_to(root)
        except (OSError, ValueError):
            continue
        if resolved.is_file():
            return resolved
    return None


def _audit_source_path(root: Path, state: Any, output_root: Path) -> Path | None:
    main = Path(state.main)
    candidates = [main if main.is_absolute() else root / main]
    candidates.extend((
        output_root / "combined" / "publication.tex",
        output_root / "publication.tex",
    ))
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved.is_file():
            return resolved
    return None


def _last_successful_step(
    root: Path,
    output_root: Path,
    reports: list[tuple[Path, dict[str, Any]]],
    review: dict[str, Any] | None,
) -> dict[str, str] | None:
    candidates: list[tuple[float, dict[str, str]]] = []
    for path, report in reports:
        if report.get("status") == "passed":
            candidates.append((_mtime(path), {
                "step": "BUILD", "at": _mtime_iso(path), "artefact": _display_path(root, path),
            }))
    review_path = root / REVIEW_PATH
    if review is not None and review.get("visual_review") in {"done", "unavailable"} and review_path.is_file():
        candidates.append((_mtime(review_path), {
            "step": "REVIEW", "at": _mtime_iso(review_path), "artefact": _display_path(root, review_path),
        }))
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[0])[1]


def _mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def _mtime_iso(path: Path) -> str:
    return datetime.fromtimestamp(_mtime(path), timezone.utc).isoformat(timespec="seconds")


def _display_path(root: Path, path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return path.resolve().relative_to(root).as_posix()
    except (OSError, ValueError):
        return str(path)


def _unique_diagnostics(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for item in items:
        key = (item.get("code"), item.get("message"), item.get("file"), item.get("line"))
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result
