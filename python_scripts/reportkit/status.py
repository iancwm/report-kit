"""Re-hydrate the loop from disk alone (spec §4.8).

``reportkit status`` reconstructs the target, intent, brief result, last
successful step, open diagnostics, visual-review state, and next action from
the consumer project. It keeps no process-local state between invocations.
"""
from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any

from .composition_audit import audit_source, find_brief
from .config import load_publication_config, resolve_output
from .loop import next_step, target_payload
from .review import read_review
from .target import TargetState, load_target, target_gate

STATUS_SCHEMA_VERSION = "1.0.0"


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _latest_build_report(root: Path) -> tuple[Path | None, dict[str, Any] | None]:
    """Find the newest build manifest under the configured output directory."""
    try:
        config = load_publication_config(root / "publication.yaml")
        output = resolve_output(config, root) or (root / "build")
    except (OSError, ValueError):
        output = root / "build"
    reports = [path for path in output.glob("**/build-report.json") if path.is_file()]
    if not reports:
        return None, None
    report_path = max(reports, key=lambda path: path.stat().st_mtime)
    return report_path, _read_json(report_path)


def _latest_step(root: Path, state: TargetState, report_path: Path | None, report: dict[str, Any] | None) -> dict[str, Any] | None:
    """Infer the last completed loop stage from persisted artifact mtimes."""
    candidates: list[tuple[float, str, Path]] = []

    def add(step: str, path: Path | None) -> None:
        if path is None:
            return
        try:
            if path.is_file():
                candidates.append((path.stat().st_mtime, step, path))
        except OSError:
            return

    intent_path = root / ".reportkit" / "intent.json"
    add("LOCK", intent_path)
    brief = find_brief(root, state)
    add("SCAFFOLD", brief)

    if state.source_mode == "tex":
        main = root / state.main
        add("AUTHOR", main)
    else:
        manuscript = root / "manuscript"
        if manuscript.is_dir():
            for path in manuscript.rglob("*.md"):
                if path.is_file() and path.name.lower() not in {"readme.md", "template.md"}:
                    add("AUTHOR", path)

    if report_path is not None and report and (
        report.get("passed") is True or report.get("status") == "passed"
    ):
        add("BUILD", report_path)
    review = root / "build" / "review.json"
    add("REVIEW", review)

    if not candidates:
        return None
    timestamp, step, path = max(candidates, key=lambda item: item[0])
    return {
        "step": step,
        "at": datetime.fromtimestamp(timestamp).astimezone().isoformat(timespec="seconds"),
        "artefact": str(path.relative_to(root)) if path.is_relative_to(root) else str(path),
    }


def collect_status(source_root: Path) -> dict[str, Any]:
    """Return the publication state reconstructed from ``source_root``."""
    root = Path(source_root).resolve()
    state = load_target(root)
    diagnostics = list(target_gate(state))
    report_path, report = _latest_build_report(root)

    # The latest build report is the durable record of previous build
    # diagnostics. It is replaced on each build, so findings from an older
    # manifest are no longer considered open.
    if report:
        build_diagnostics = report.get("diagnostics", [])
        if isinstance(build_diagnostics, dict):
            build_diagnostics = build_diagnostics.get("diagnostics", build_diagnostics.get("issues", []))
        if not isinstance(build_diagnostics, list):
            build_diagnostics = []
        diagnostics.extend(
            item for item in build_diagnostics
            if isinstance(item, dict) and item.get("severity") in {"error", "warning"}
        )

    brief_path = find_brief(root, state)
    brief_status: dict[str, Any] | None = None
    if brief_path is not None:
        source = (root / state.main) if state.source_mode == "tex" else None
        if source is None or not source.is_file():
            if report_path is not None:
                generated = report_path.parent / "publication.tex"
                source = generated if generated.is_file() else None
        audit = audit_source(source, brief_path, state) if source is not None and source.is_file() else None
        if audit is not None:
            diagnostics.extend(
                item for item in audit.get("diagnostics", [])
                if isinstance(item, dict) and item.get("severity") in {"error", "warning"}
            )
        brief_status = {
            "path": str(brief_path.relative_to(root)) if brief_path.is_relative_to(root) else str(brief_path),
            "passed": audit.get("passed") if audit is not None else None,
        }

    review = read_review(root) or {}
    visual_review = review.get("visual_review")
    if visual_review not in {"done", "unavailable"}:
        visual_review = None
    caveat = None
    if visual_review == "unavailable":
        caveat = "Rendered pages could not be viewed in this host; state that visual review was unavailable in the delivery message."

    unique_diagnostics: dict[str, dict[str, Any]] = {}
    for item in diagnostics:
        if isinstance(item, dict):
            unique_diagnostics.setdefault(json.dumps(item, sort_keys=True, ensure_ascii=False), item)
    diagnostics = list(unique_diagnostics.values())
    passed = not any(item.get("severity") == "error" for item in diagnostics)
    result: dict[str, Any] = {
        "schema_version": STATUS_SCHEMA_VERSION,
        "passed": passed,
        "target": target_payload(state),
        "intent": state.intent,
        "brief": brief_status,
        "last_step": _latest_step(root, state, report_path, report),
        "diagnostics": diagnostics,
        "visual_review": visual_review,
        "delivery_caveat": caveat,
    }
    result["next_step"] = next_step("status", state, result)
    return result
