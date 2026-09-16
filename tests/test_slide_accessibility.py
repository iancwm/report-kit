"""B4: inspect the canonical slide PDF's shipped accessibility contract."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

import pytest

from publication_pipeline.scripts.inspect_pdf import inspect_slide_accessibility
from reportkit.publications import resolve_build_target

REPO = Path(__file__).resolve().parents[1]


def _stage_slide_fixture(destination: Path) -> str:
    templates = REPO / "latex_templates"
    for source in (
        list(templates.glob("*.cls"))
        + list(templates.glob("*.def"))
        + list(templates.glob("reportkit-*.tex"))
        + list(templates.glob("*.sty"))
        + list((templates / "themes").glob("*.sty"))
        + list((templates / "publication_types").glob("*.sty"))
    ):
        shutil.copy(source, destination / source.name)
    font_data = REPO / "font_data"
    staged_fonts = destination / "font_data"
    staged_fonts.mkdir()
    for source in font_data.glob("GoogleSans-*.ttf"):
        shutil.copy(source, staged_fonts / source.name)
    fixture = templates / "examples" / "presentation_acceptance_test.tex"
    shutil.copy(fixture, destination / fixture.name)
    return fixture.name


@pytest.mark.skipif(shutil.which("lualatex") is None, reason="requires LuaLaTeX")
def test_canonical_slide_pdf_satisfies_accessibility_contract(tmp_path: Path) -> None:
    fixture_name = _stage_slide_fixture(tmp_path)
    environment = dict(os.environ, LC_ALL="C")
    for _ in range(2):
        process = subprocess.run(
            [shutil.which("lualatex") or "lualatex", "-file-line-error", "-interaction=nonstopmode", "-halt-on-error", fixture_name],
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            text=True,
            timeout=180,
        )
        assert process.returncode == 0, (process.stdout + "\n" + process.stderr)[-6000:]

    target = resolve_build_target("presentation", "executive", engine="lualatex", repo_root=REPO)
    result = inspect_slide_accessibility(
        tmp_path / "presentation_acceptance_test.pdf",
        expected_metadata={
            "title": "Every presentation composition, once - Phase B compile coverage, not a real deck",
            "author": "Test build",
            "subject": "Presentation accessibility acceptance",
            "keywords": "ReportKit, presentation, accessibility",
        },
        expected_language="en-US",
        minimum_bookmarks=1,
        expected_bookmark_titles=[
            "Message and evidence",
            "Visuals",
            "Structure",
            "Appendix: Chart, table, and architecture aliases",
        ],
        minimum_meaningful_links=1,
        expected_actual_text=3,
        tagged_pdf_status=str(target.accessibility["tagged_pdf"]),
        tagged_pdf_reason=str(target.accessibility["tagged_pdf_reason"]),
    )

    assert result["passed"], result["diagnostics"]
    checks = result["slide_accessibility"]
    assert all(check["passed"] for check in checks["metadata"].values())
    assert checks["catalog_language"]["passed"] is True
    assert checks["bookmarks"]["passed"] is True
    assert checks["links"]["passed"] is True
    assert checks["diagram_actual_text"]["passed"] is True
    assert checks["tagged_pdf"] == {
        "status": "unsupported",
        "reason": "The pinned LaTeX format has not yet passed the documented tagging spike.",
        "verified": True,
    }
