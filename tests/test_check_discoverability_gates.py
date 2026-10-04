from __future__ import annotations

import json
from pathlib import Path
import subprocess


REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "publication_pipeline" / "example_publication" / "image-slots.yaml"


def _run(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(REPO / "reportkit"), *arguments], capture_output=True, text=True)


def _project(tmp_path: Path, source_mode: str) -> Path:
    root = tmp_path / "publication"
    target = ("--publication-type", "technical-report", "--theme", "default", "--source-mode", source_mode)
    for command in (
        ("target", "set", "--source-root", str(root), *target, "--request", "test publication", "--json"),
        ("init", str(root), *target, "--json"),
    ):
        result = _run(*command)
        assert result.returncode == 0, result.stdout + result.stderr
    return root


def _check(root: Path) -> tuple[int, dict]:
    result = _run("check", "--source-root", str(root), "--json")
    return result.returncode, json.loads(result.stdout)


def _codes(payload: dict) -> list[str]:
    return [item["code"] for item in payload["diagnostics"]]


def _image_validation_codes(payload: dict) -> list[str]:
    return [code for code in _codes(payload) if code.startswith("RK_VALIDATION_") and "IMAGE" in code]


def test_check_warns_when_the_composition_brief_is_missing(tmp_path: Path) -> None:
    root = _project(tmp_path, "markdown")
    (root / "composition-brief.json").unlink()
    exit_code, payload = _check(root)
    assert exit_code == 0
    assert payload["passed"] is True
    warning = next(item for item in payload["diagnostics"] if item["code"] == "RK_COMPOSITION_BRIEF_MISSING")
    assert warning["severity"] == "warning"
    assert "reportkit init" in warning["remediation"]


def test_check_is_quiet_about_the_brief_when_one_exists(tmp_path: Path) -> None:
    root = _project(tmp_path, "markdown")
    _, payload = _check(root)
    assert "RK_COMPOSITION_BRIEF_MISSING" not in _codes(payload)


def test_undeclared_project_gets_no_brief_warning(tmp_path: Path) -> None:
    root = tmp_path / "publication"
    assert _run("init", str(root), "--json").returncode == 0
    # Verified 2026-10-04: an init without target flags fails check with
    # RK_CONFIG_BUILD_TARGET (empty publication_type), not RK_TARGET_UNDECLARED.
    _, payload = _check(root)
    assert payload["passed"] is False
    assert "RK_COMPOSITION_BRIEF_MISSING" not in _codes(payload)


def test_tex_project_with_an_image_manifest_gets_one_actionable_error(tmp_path: Path) -> None:
    root = _project(tmp_path, "tex")
    (root / "image-slots.yaml").write_text(MANIFEST.read_text(encoding="utf-8"), encoding="utf-8")
    exit_code, payload = _check(root)
    assert exit_code == 3
    assert payload["passed"] is False
    error = next(item for item in payload["diagnostics"] if item["code"] == "RK_IMAGE_SLOTS_TEX_MODE")
    assert error["severity"] == "error"
    assert "Markdown-only" in error["message"]
    assert _image_validation_codes(payload) == []


def test_tex_project_with_an_image_marker_in_main_is_flagged(tmp_path: Path) -> None:
    root = _project(tmp_path, "tex")
    main = root / "report.tex"
    main.write_text(
        main.read_text(encoding="utf-8").replace(
            "\\end{document}", "[[REPORTKIT-IMAGE:img:pump-housing]]\n\\end{document}",
        ),
        encoding="utf-8",
    )
    _, payload = _check(root)
    assert "RK_IMAGE_SLOTS_TEX_MODE" in _codes(payload)


def test_commented_image_marker_in_tex_is_ignored(tmp_path: Path) -> None:
    root = _project(tmp_path, "tex")
    main = root / "report.tex"
    main.write_text(
        main.read_text(encoding="utf-8").replace(
            "\\end{document}", "% [[REPORTKIT-IMAGE:img:pump-housing]]\n\\end{document}",
        ),
        encoding="utf-8",
    )
    _, payload = _check(root)
    assert "RK_IMAGE_SLOTS_TEX_MODE" not in _codes(payload)


def test_markdown_project_keeps_image_validation(tmp_path: Path) -> None:
    root = _project(tmp_path, "markdown")
    (root / "image-slots.yaml").write_text(MANIFEST.read_text(encoding="utf-8"), encoding="utf-8")
    _, payload = _check(root)
    assert "RK_VALIDATION_ORPHAN_IMAGE_DECLARATION" in _codes(payload)
    assert "RK_IMAGE_SLOTS_TEX_MODE" not in _codes(payload)


def test_tex_check_payload_has_no_image_slot_fields_but_markdown_does(tmp_path: Path) -> None:
    tex = _project(tmp_path / "tex", "tex")
    (tex / "image-slots.yaml").write_text(MANIFEST.read_text(encoding="utf-8"), encoding="utf-8")
    _, tex_payload = _check(tex)
    assert tex_payload["image_slots"] == {}
    assert tex_payload["unresolved_image_slots"] == []
    md = _project(tmp_path / "md", "markdown")
    (md / "image-slots.yaml").write_text(MANIFEST.read_text(encoding="utf-8"), encoding="utf-8")
    _, md_payload = _check(md)
    assert md_payload["image_slots"]
    assert md_payload["unresolved_image_slots"]
