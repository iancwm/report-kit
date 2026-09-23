"""Phase D contract, branding and fixture coverage for the venture theme.

The critical Phase D gate is the last test here: the shared
presentation-semantic smoke document compiles under executive and venture
with nothing but the class option changed, and the pixels differ
materially. Structural checks alongside it prove there is no venture copy of
reportkit-presentation.sty and no venture-only composition name.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

import pytest

from reportkit.config import BRAND_KEYS, load_publication_config, resolve_effective_theme
from reportkit.publications import PUBLICATION_TYPES, THEMES, resolve_build_target
from reportkit.theme_overrides import materialize_chart_overrides, render_tex_overrides, validate_tex_overrides

REPO = Path(__file__).resolve().parents[1]
TEMPLATES = REPO / "latex_templates"
EXAMPLE = TEMPLATES / "examples" / "venture-presentation"
PRESENTATION = TEMPLATES / "publication_types" / "reportkit-presentation.sty"
VENTURE_STY = TEMPLATES / "themes" / "reportkit-theme-venture.sty"
VENTURE_SLIDES = TEMPLATES / "themes" / "reportkit-theme-venture-slides.sty"

_REQUIRES_LUALATEX = pytest.mark.skipif(
    shutil.which("lualatex") is None
    or shutil.which("kpsewhich") is None
    or subprocess.run(["kpsewhich", "siunitx.sty"], capture_output=True, text=True).returncode != 0,
    reason="requires the LuaLaTeX toolchain with siunitx",
)


def _code(path: Path) -> str:
    return "\n".join(line for line in path.read_text(encoding="utf-8").splitlines() if not line.lstrip().startswith("%"))


def _compositions() -> set[str]:
    return set(re.findall(r"\\NewDocumentEnvironment\{([a-z]+)\}", PRESENTATION.read_text(encoding="utf-8")))


def test_venture_registry_record_shares_the_presentation_publication_type() -> None:
    theme = THEMES["venture"]
    assert theme["renderers"] == ["slides"]
    assert theme["required_engine"] == "lualatex"
    assert theme["common_package"] == "reportkit-theme-venture"
    assert theme["renderer_adapters"] == {"slides": "reportkit-theme-venture-slides"}
    assert theme["brand_overrides"] is True
    # Not promoted until pinned-toolchain visual review, as executive was.
    assert theme["stability"] == "experimental"
    assert [name for name, record in PUBLICATION_TYPES.items() if "venture" in record["themes"]] == ["presentation"]
    target = resolve_build_target("presentation", "venture", engine="lualatex", repo_root=REPO)
    assert target.publication_package == "reportkit-presentation"
    assert target.brand_overrides is True
    assert target.canvas == {"width_mm": 160, "height_mm": 90}


def test_there_is_no_venture_composition_layer() -> None:
    assert not list((TEMPLATES / "publication_types").glob("*venture*"))
    for path in (VENTURE_STY, VENTURE_SLIDES):
        code = _code(path)
        assert "\\NewDocumentEnvironment" not in code and "\\newenvironment" not in code
        assert "\\RequirePackage{reportkit-presentation}" not in code
    presentation_code = _code(PRESENTATION)
    assert "venture" not in presentation_code
    assert "executive" not in presentation_code
    # Every frame-level composition reports one renderer-neutral surface role.
    roles = set(re.findall(r"\\RKTokPresentationSurface\{([a-z]+)\}", presentation_code))
    assert roles == {"opening", "divider", "statement", "metric", "closing", "content"}


def test_surface_roles_are_theme_decisions() -> None:
    executive = (TEMPLATES / "themes" / "reportkit-theme-executive-slides.sty").read_text(encoding="utf-8")
    venture = VENTURE_SLIDES.read_text(encoding="utf-8")
    assert "\\renewcommand{\\RKTokPresentationSurface}[1]{}" in executive
    for role in ("opening", "divider", "statement", "closing"):
        assert f"\\@namedef{{rkventure@inverse@{role}}}{{}}" in venture
    for role in ("metric", "content"):
        assert f"rkventure@inverse@{role}" not in venture


def test_venture_tokens_are_reviewed_values_not_placeholders() -> None:
    python_theme = (REPO / "python_scripts" / "reportkit" / "themes" / "venture.py").read_text(encoding="utf-8")
    for text in (VENTURE_STY.read_text(encoding="utf-8"), VENTURE_SLIDES.read_text(encoding="utf-8"), python_theme):
        assert "placeholder" not in text.lower()
    assert 'PRIMARY = "#4F46E5"' in python_theme
    assert "\\definecolor{Accent}{HTML}{4F46E5}" in VENTURE_STY.read_text(encoding="utf-8")


def test_venture_chart_theme_matches_latex_palette_and_contract() -> None:
    pytest.importorskip("matplotlib")
    pytest.importorskip("numpy")
    pytest.importorskip("pandas")
    import reportkit_viz as rkv
    from reportkit.themes import get_theme

    theme = get_theme("venture")
    assert rkv.validate_palette_against_latex(VENTURE_STY, theme.latex_colors) == []
    assert rkv.validate_theme_contract_against_latex("venture") == []
    assert set(theme.figure_sizes) == {"slide-main", "slide-half", "slide-hero"}
    assert all(width <= 136 / 25.4 + 1e-9 for width, _ in theme.figure_sizes.values())


def test_fixture_brand_is_exactly_the_d6_surface_and_resolves_once() -> None:
    config = load_publication_config(EXAMPLE / "publication.yaml")
    assert set(config["brand"]) <= set(BRAND_KEYS)
    effective = resolve_effective_theme(config, source_root=EXAMPLE)
    assert effective.theme == "venture"
    assert effective.brand.logo == (EXAMPLE / "assets" / "lumiquay-mark.pdf").resolve()
    assert effective.logo_hash == hashlib.sha256(effective.brand.logo.read_bytes()).hexdigest()
    tex = render_tex_overrides(effective)
    assert validate_tex_overrides(tex, effective) == []
    chart = materialize_chart_overrides(effective)
    assert chart["primary"] == effective.latex_colors["LinkBlue"] == effective.latex_colors["Accent"] == "#0E7C66"
    assert chart["secondary"] == effective.latex_colors["Research"] == "#FFB020"
    assert chart["hashes"] == {"palette": effective.palette_hash, "font": effective.font_hash, "logo": effective.logo_hash}


def test_fixture_is_a_twelve_slide_pitch_built_from_shared_compositions_only() -> None:
    report = (EXAMPLE / "report.tex").read_text(encoding="utf-8")
    manuscript = (EXAMPLE / "manuscript" / "01-pitch.md").read_text(encoding="utf-8")
    fragments = {path.name: path.read_text(encoding="utf-8") for path in (EXAMPLE / "fragments").glob("*.tex")}
    assert len(re.findall(r"\\begin\{frame\}", report)) == 12
    # The title slide comes from presentation.tex's front matter in the pipeline.
    assert manuscript.count("```reportkit") == 11
    used = set(re.findall(r"\\begin\{([a-z]+)\}", report + "\n".join(fragments.values()))) - {"frame", "document", "diagram", "reportmatrix"}
    directives = set(re.findall(r"```reportkit ([a-z]+)", manuscript))
    assert used <= _compositions(), used - _compositions()
    assert directives <= _compositions()
    story = (report + manuscript).lower()
    for required in ("problem", "pulse", "annual recurring revenue", "market", "prediction without", "team", "seed round"):
        assert required in story
    assert all(r"\draw" not in text and r"\node" not in text for text in fragments.values())
    direct = set(re.findall(r"fragments/(fig-[a-z-]+\.tex)", report))
    pipeline = set(re.findall(r"fragment: (fig-[a-z-]+\.tex)", manuscript))
    assert direct == pipeline == set(fragments)
    assert "fictional" in report.lower()


@_REQUIRES_LUALATEX
def test_canonical_venture_fixture_compiles_with_brand_overrides(tmp_path: Path) -> None:
    pytest.importorskip("pymupdf")
    from scripts.visual_qa_venture import compile_fixture, inspect_fixture

    pdf, log, returncode, brand = compile_fixture(tmp_path)
    assert returncode == 0, log[-8000:]
    assert brand["override_errors"] == []
    assert brand["effective_theme"]["hashes"]["logo"]
    result = inspect_fixture(pdf, log, brand)
    assert result["passed"], result["diagnostics"]
    assert result["page_count"] == 12
    assert "REPORTKIT-PRESENTATION-ASSERTION-FIT=invalid" not in log


@_REQUIRES_LUALATEX
@pytest.mark.skipif(shutil.which("pandoc") is None, reason="requires pandoc")
def test_venture_fixture_builds_through_the_pipeline_with_a_staged_hashed_logo(tmp_path: Path) -> None:
    pytest.importorskip("pymupdf")
    source = tmp_path / "venture"
    shutil.copytree(EXAMPLE, source, ignore=shutil.ignore_patterns("build", "__pycache__"))
    output = tmp_path / "build"
    process = subprocess.run(
        [sys.executable, str(REPO / "publication_pipeline" / "scripts" / "publication_build.py"),
         "--mode", "combined", "--source-root", str(source), "--output-root", str(output), "--json"],
        capture_output=True, text=True, timeout=600,
    )
    assert process.returncode == 0, process.stdout[-4000:] + process.stderr[-4000:]
    report = json.loads((output / "combined" / "build-report.json").read_text(encoding="utf-8"))
    logo_hash = hashlib.sha256((source / "assets" / "lumiquay-mark.pdf").read_bytes()).hexdigest()
    assert {"path": "assets/lumiquay-mark.pdf", "sha256": logo_hash} in report["assets"]
    assert report["effective_theme"]["hashes"]["logo"] == logo_hash
    assert report["effective_theme"]["palette"]["Accent"] == "#0E7C66"
    overrides = (output / "combined" / "reportkit-theme-overrides.tex").read_text(encoding="utf-8")
    assert r"\newcommand{\RKBrandLogo}{assets/lumiquay-mark.pdf}" in overrides
    assert report["selection"]["theme"] == "venture"
    import pymupdf

    with pymupdf.open(output / "combined" / report["pdf"]) as document:
        assert document.page_count == 12


@_REQUIRES_LUALATEX
def test_one_semantic_smoke_document_renders_materially_differently(tmp_path: Path) -> None:
    """Phase D critical gate: same source, only theme= changed."""
    pytest.importorskip("pymupdf")
    from scripts.visual_qa_venture import MATERIAL_DIFFERENCE_FLOOR, compile_smoke, pixel_difference

    pdfs = {}
    for theme in ("executive", "venture"):
        pdf, log, returncode = compile_smoke(tmp_path / theme, theme)
        assert returncode == 0, log[-8000:]
        pdfs[theme] = pdf
    executive_source = (tmp_path / "executive" / "smoke.tex").read_text(encoding="utf-8")
    venture_source = (tmp_path / "venture" / "smoke.tex").read_text(encoding="utf-8")
    assert executive_source.replace("theme=executive", "theme=venture", 1) == venture_source
    difference = pixel_difference(pdfs["executive"], pdfs["venture"])
    assert difference["page_counts"][0] == difference["page_counts"][1]
    assert difference["mean"] >= MATERIAL_DIFFERENCE_FLOOR, difference
    # Every page differs, not just an average dominated by dark frames.
    assert min(difference["per_page"]) > 1.0, difference
