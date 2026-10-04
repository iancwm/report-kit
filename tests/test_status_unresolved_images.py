from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from reportkit.status import collect_status


REPO = Path(__file__).resolve().parents[1]
ITEM = {
    "slug": "field-photo",
    "asset_state": "placeholder",
    "replacement_path": "assets/images/field-photo.jpg",
    "source_location": {"file": "manuscript/01-fixture.md", "line": 27},
    "reason": "missing image file assets/images/field-photo.jpg",
}


def _declared_project(tmp_path: Path) -> Path:
    root = tmp_path / "publication"
    result = subprocess.run(
        [
            str(REPO / "reportkit"), "target", "set", "--source-root", str(root),
            "--publication-type", "technical-report", "--theme", "default", "--source-mode", "markdown",
            "--request", "test publication", "--json",
        ],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return root


def _write_report(root: Path, unresolved: object) -> None:
    report = root / "build" / "combined" / "build-report.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps({
        "passed": True,
        "diagnostics": [],
        "unresolved_image_slots": unresolved,
    }), encoding="utf-8")


def test_status_lists_unresolved_image_slots_from_the_latest_build(tmp_path: Path) -> None:
    root = _declared_project(tmp_path)
    _write_report(root, [ITEM])
    status = collect_status(root)
    assert status["unresolved_images"] == [{
        "slug": "field-photo",
        "replacement_path": "assets/images/field-photo.jpg",
        "reason": "missing image file assets/images/field-photo.jpg",
    }]
    assert "field-photo" in status["image_caveat"]


def test_status_has_no_image_caveat_when_every_slot_is_resolved(tmp_path: Path) -> None:
    root = _declared_project(tmp_path)
    _write_report(root, [])
    status = collect_status(root)
    assert status["unresolved_images"] == []
    assert status["image_caveat"] is None


def test_status_without_a_build_report_has_empty_image_fields(tmp_path: Path) -> None:
    status = collect_status(_declared_project(tmp_path))
    assert status["unresolved_images"] == []
    assert status["image_caveat"] is None


@pytest.mark.parametrize("unresolved", ["field-photo", {"slug": "x"}, [{"reason": "no slug"}, "text", None]])
def test_status_skips_malformed_unresolved_entries(tmp_path: Path, unresolved: object) -> None:
    root = _declared_project(tmp_path)
    _write_report(root, unresolved)
    status = collect_status(root)
    assert status["unresolved_images"] == []
    assert status["image_caveat"] is None


def test_delivery_next_step_names_unresolved_images(tmp_path: Path) -> None:
    root = _declared_project(tmp_path)
    _write_report(root, [ITEM])
    (root / "build" / "review.json").write_text(json.dumps({"visual_review": "done"}), encoding="utf-8")
    status = collect_status(root)
    assert status["next_step"]["command"].startswith("Deliver the publication")
    assert "image_caveat" in status["next_step"]["reason"]


def test_status_with_image_fields_matches_the_schema(tmp_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((REPO / "schemas" / "reportkit-status.schema.json").read_text(encoding="utf-8"))
    root = _declared_project(tmp_path)
    for unresolved in ([ITEM], []):
        _write_report(root, unresolved)
        jsonschema.Draft202012Validator(schema).validate(collect_status(root))
    assert {"unresolved_images", "image_caveat"} <= set(schema["properties"])


def test_human_status_prints_the_image_caveat(tmp_path: Path) -> None:
    root = _declared_project(tmp_path)
    _write_report(root, [ITEM])
    result = subprocess.run(
        [str(REPO / "reportkit"), "status", "--source-root", str(root)],
        capture_output=True, text=True,
    )
    assert "image caveat:" in result.stdout, result.stdout + result.stderr
    assert "field-photo" in result.stdout
