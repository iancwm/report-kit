"""Phase C contract and fixture coverage for the stable executive theme."""
from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess

import pytest

from reportkit.publications import PUBLICATION_TYPES, RENDERERS, THEMES

REPO = Path(__file__).resolve().parents[1]
EXAMPLE = REPO / "latex_templates" / "examples" / "executive-presentation"


def test_executive_target_is_stable_and_canvas_bound() -> None:
    assert RENDERERS["slides"]["stability"] == "stable"
    assert THEMES["executive"]["stability"] == "stable"
    assert PUBLICATION_TYPES["presentation"]["stability"] == "stable"
    assert RENDERERS["slides"]["geometry"] == {"kind": "canvas", "canvas": {"width_mm": 160, "height_mm": 90}}


def test_executive_tokens_are_reviewed_not_placeholder_shells() -> None:
    theme = (REPO / "latex_templates" / "themes" / "reportkit-theme-executive.sty").read_text(encoding="utf-8")
    adapter = (REPO / "latex_templates" / "themes" / "reportkit-theme-executive-slides.sty").read_text(encoding="utf-8")
    python_theme = (REPO / "python_scripts" / "reportkit" / "themes" / "executive.py").read_text(encoding="utf-8")
    for text in (theme, adapter, python_theme):
        assert "EXPERIMENTAL" not in text
        assert "placeholder" not in text.lower()
    assert "0B7285" in theme
    assert "C26A2D" in theme
    assert 'ACCENT = "#0B7285"' in python_theme


def test_executive_fixture_covers_required_deck_story_and_shared_primitives() -> None:
    report = (EXAMPLE / "report.tex").read_text(encoding="utf-8")
    manuscript = (EXAMPLE / "manuscript" / "01-deck.md").read_text(encoding="utf-8")
    fragments = {path.name: path.read_text(encoding="utf-8") for path in (EXAMPLE / "fragments").glob("*.tex")}
    assert len(re.findall(r"\\begin\{frame\}(?:\[plain\])?", report)) == 10
    assert manuscript.count("```reportkit") == 9
    for required in ("title", "evidence", "architecture", "matrix", "chart", "table", "roadmap", "recommendation"):
        assert required in (report + manuscript).lower()
    assert "https://example.com/nexagrid-brief" in fragments["fig-recommendation.tex"]
    assert all(r"\draw" not in text and r"\node" not in text for text in fragments.values())
    assert "NexaGrid" in report
    assert "AWS" not in report + manuscript


def test_direct_and_pipeline_fixtures_share_all_trusted_fragments() -> None:
    report = (EXAMPLE / "report.tex").read_text(encoding="utf-8")
    manuscript = (EXAMPLE / "manuscript" / "01-deck.md").read_text(encoding="utf-8")
    direct = set(re.findall(r"fragments/(fig-[a-z-]+\.tex)", report))
    pipeline = set(re.findall(r"fragment: (fig-[a-z-]+\.tex)", manuscript))
    assert direct == pipeline == {f"fig-{name}.tex" for name in ("evidence", "architecture", "process", "matrix", "chart", "table", "timeline", "roadmap", "recommendation")}
    assert all((EXAMPLE / "fragments" / name).is_file() for name in direct)
    assert (EXAMPLE / "figures.py").is_file()


def test_executive_chart_theme_matches_latex_palette() -> None:
    pytest.importorskip("matplotlib")
    pytest.importorskip("numpy")
    pytest.importorskip("pandas")
    import reportkit_viz as rkv
    from reportkit.themes import get_theme

    theme = get_theme("executive")
    style = REPO / "latex_templates" / "themes" / "reportkit-theme-executive.sty"
    assert rkv.validate_palette_against_latex(style, theme.latex_colors) == []


def test_executive_viz_contract_resolves_from_repository_root() -> None:
    pytest.importorskip("matplotlib")
    pytest.importorskip("numpy")
    pytest.importorskip("pandas")
    import reportkit_viz as rkv

    assert rkv.theme_file_for("executive") == REPO / "latex_templates" / "themes" / "reportkit-theme-executive.sty"
    assert rkv.validate_theme_contract_against_latex("executive") == []


@pytest.mark.skipif(
    shutil.which("lualatex") is None
    or shutil.which("kpsewhich") is None
    or subprocess.run(["kpsewhich", "siunitx.sty"], capture_output=True, text=True).returncode != 0,
    reason="requires the pinned LuaLaTeX toolchain with siunitx",
)
def test_canonical_executive_fixture_compiles_and_has_ten_frames(tmp_path: Path) -> None:
    pytest.importorskip("pymupdf")
    from scripts.visual_qa_executive import compile_fixture, inspect_fixture

    pdf, log, returncode = compile_fixture(tmp_path)
    assert returncode == 0, log[-8000:]
    result = inspect_fixture(pdf, log)
    assert result["passed"], result["diagnostics"]
    assert result["page_count"] == 10
