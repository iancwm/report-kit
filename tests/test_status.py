from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess

from reportkit.diagnostics import make_diagnostic


REPO = Path(__file__).resolve().parents[1]


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _status(root: Path) -> dict:
    process = subprocess.run(
        [str(REPO / "reportkit"), "status", "--source-root", str(root), "--json"],
        capture_output=True, text=True,
    )
    assert process.returncode == 0, process.stderr + process.stdout
    return json.loads(process.stdout)


def test_fresh_subprocess_reconstructs_status_from_disk(tmp_path: Path) -> None:
    root = tmp_path / "publication"
    root.mkdir()
    (root / "publication.yaml").write_text(
        "title: Status fixture\n"
        "document:\n"
        "  publication_type: technical-report\n"
        "  theme: default\n"
        "  source_mode: tex\n"
        "  main: report.tex\n",
        encoding="utf-8",
    )
    (root / "report.tex").write_text("\\documentclass{reportkit}\n\\begin{document}Fixture\\end{document}\n", encoding="utf-8")
    intent = {
        "schema_version": "1.0.0",
        "request": "A technical report about resilient ports.",
        "publication_type": "technical-report",
        "theme": "default",
        "source_mode": "tex",
        "visual_reference": "assets/reference/example.pdf",
        "composition_brief": "composition-brief.json",
        "decided_by": "user-confirmed",
        "locked_at": "2026-09-29T10:00:00Z",
    }
    _write(root / ".reportkit" / "intent.json", intent)
    _write(root / "composition-brief.json", {"required": ["openingvisual"]})

    warning = make_diagnostic("target_contract", "legacy target was defaulted", code="RK_TARGET_IMPLICIT")
    build_report = {
        "schema_version": 4,
        "status": "passed",
        "selection": {"publication_type": "technical-report", "theme": "default", "matches_intent": True},
        "diagnostics": {"diagnostics": [warning], "passed": True},
    }
    report_path = root / "build" / "combined" / "build-report.json"
    _write(report_path, build_report)
    os.utime(report_path, (1_790_000_000, 1_790_000_000))

    review = {
        "schema_version": "1.0.0",
        "pdf": "build/combined/publication.pdf",
        "publication_type": "technical-report",
        "theme": "default",
        "visual_review": "unavailable",
        "checklist": [],
        "reviewed_at": "2026-09-29T11:00:00Z",
    }
    review_path = root / "build" / "review.json"
    _write(review_path, review)
    os.utime(review_path, (1_790_000_060, 1_790_000_060))

    first = _status(root)
    assert first["target"]["publication_type"] == "technical-report"
    assert first["target"]["theme"] == "default"
    assert first["target"]["line"].startswith("TARGET structure=technical-report look=default")
    assert first["intent"] == intent
    assert first["brief"] == {"path": "composition-brief.json", "passed": True}
    assert first["last_step"] == {
        "step": "REVIEW",
        "at": datetime.fromtimestamp(1_790_000_060, timezone.utc).isoformat(timespec="seconds"),
        "artefact": "build/review.json",
    }
    assert first["visual_review"] == "unavailable"
    assert "Visual review was unavailable" in first["delivery_caveat"]
    assert any(item["code"] == "RK_TARGET_IMPLICIT" for item in first["diagnostics"])

    # A second process sees the changed files, with no dependence on the first
    # call's in-memory state.
    review["visual_review"] = "done"
    _write(review_path, review)
    os.utime(review_path, (1_790_000_120, 1_790_000_120))
    second = _status(root)
    assert second["intent"] == intent
    assert second["visual_review"] == "done"
    assert second["delivery_caveat"] is None
    assert second["last_step"]["step"] == "REVIEW"
    assert second["last_step"]["at"] == datetime.fromtimestamp(
        1_790_000_120, timezone.utc,
    ).isoformat(timespec="seconds")


def test_status_without_saved_intent_or_build_artifacts_is_reconstructable(tmp_path: Path) -> None:
    (tmp_path / "publication.yaml").write_text("title: Empty status fixture\n", encoding="utf-8")
    payload = _status(tmp_path)
    assert payload["intent"] is None
    assert payload["brief"] == {"path": None, "passed": None}
    assert payload["last_step"] is None
    assert payload["visual_review"] is None
    assert payload["delivery_caveat"] is None
    assert payload["next_step"]["command"] == "deliver"
