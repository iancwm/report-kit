"""Phase F1 coverage for the executive-brief publication type.

Registry shape, primitive reuse (no parallel executive component library),
the shared exhibit module's theme contract, the 2-8 page acceptance fixture
under both registered themes, and the Markdown pipeline entrypoint.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess

import pytest

from reportkit.config import resolve_document
from reportkit.publications import (
    PUBLICATION_TYPES,
    THEMES,
    PublicationRegistryError,
    check_publication_registry,
    resolve_build_target,
)
from reportkit.registry import generate_registry

REPO = Path(__file__).resolve().parents[1]
TEMPLATES = REPO / "latex_templates"
PUBLICATION_TYPES_DIR = TEMPLATES / "publication_types"
BRIEF_STY = PUBLICATION_TYPES_DIR / "reportkit-executive-brief.sty"
EXHIBITS_STY = PUBLICATION_TYPES_DIR / "reportkit-exhibits.sty"
EQUITY_STY = PUBLICATION_TYPES_DIR / "reportkit-equity-research.sty"
EXECUTIVE_PAGED = TEMPLATES / "themes" / "reportkit-theme-executive-paged.sty"
INSTITUTIONAL_COMMON = TEMPLATES / "themes" / "reportkit-theme-institutional-research.sty"
EXAMPLE = TEMPLATES / "examples" / "executive-brief"
FIXTURES = {
    "executive": "report.tex",
    "institutional-research": "report-institutional-research.tex",
}
REQUIRED_SECTIONS = ("Recommendation", "Key findings", "Evidence", "Implication", "Risks", "Next steps", "Sources")

requires_lualatex = pytest.mark.skipif(shutil.which("lualatex") is None, reason="lualatex not on PATH")


def _code(path: Path) -> str:
    """Return TeX source with comments removed."""
    return "\n".join(re.sub(r"(?<!\\)%.*", "", line) for line in path.read_text(encoding="utf-8").splitlines())


def test_executive_brief_is_registered_for_exactly_its_two_themes() -> None:
    record = PUBLICATION_TYPES["executive-brief"]
    assert record["renderer"] == "paged"
    assert record["paper"] == "letter"
    assert record["themes"] == ["executive", "institutional-research"]
    assert record["default_target"] == {"theme": "executive", "paper": "letter"}
    assert record["template"] == "executive-brief.tex"
    assert record["package"] == "reportkit-executive-brief"
    # Experimental until the pinned-toolchain visual review approves it.
    assert record["stability"] == "experimental"
    assert check_publication_registry(REPO) == []


def test_executive_theme_gains_a_paged_adapter_without_losing_slides() -> None:
    executive = THEMES["executive"]
    assert sorted(executive["renderers"]) == ["paged", "slides"]
    assert executive["renderer_adapters"] == {
        "paged": "reportkit-theme-executive-paged",
        "slides": "reportkit-theme-executive-slides",
    }
    assert PUBLICATION_TYPES["presentation"]["themes"] == ["executive"]


@pytest.mark.parametrize("theme", sorted(FIXTURES))
def test_both_brief_targets_resolve(theme: str) -> None:
    target = resolve_build_target("executive-brief", theme, repo_root=REPO)
    assert target.renderer == "paged"
    assert target.class_name == "reportkit"
    assert target.engine == "lualatex"
    assert target.paper == "letter"
    assert target.template == "executive-brief.tex"
    assert target.publication_package == "reportkit-executive-brief"
    expected_adapter = {
        "executive": "reportkit-theme-executive-paged",
        "institutional-research": "reportkit-theme-institutional-research-paged",
    }[theme]
    assert target.renderer_adapter == expected_adapter


def test_omitted_paper_defaults_to_the_publication_types_registered_paper() -> None:
    brief = resolve_document({"document": {"publication_type": "executive-brief", "theme": "executive"}})
    assert brief["paper"] == "letter"
    assert resolve_document({})["paper"] == "a4"


@pytest.mark.parametrize("theme", ("default", "technical"))
def test_unregistered_themes_are_rejected_with_candidates(theme: str) -> None:
    with pytest.raises(PublicationRegistryError) as error:
        resolve_build_target("executive-brief", theme, repo_root=REPO)
    assert error.value.diagnostic["candidates"] == ["executive", "institutional-research"]


def test_brief_reuses_shared_primitives_instead_of_a_parallel_library() -> None:
    code = _code(BRIEF_STY)
    assert r"\RequirePackage{reportkit-exhibits}" in code
    declared = set(re.findall(r"\\NewDocument(?:Environment|Command)\{\\?([A-Za-z@]+)\}", code))
    public = {name for name in declared if "@" not in name}
    # Only what spec section 14's reused components do not already cover.
    assert public == {"briefheader", "briefmeta", "briefactions", "briefaction", "briefsources"}
    for reused in ("metric", "decisionpoint", "redflag", "assumption", "exhibit", "exhibitpair",
                   "exhibitgrid", "exhibitpane", "financialtable", "source"):
        assert reused not in declared
    assert r"\definecolor" not in code
    assert r"\fontsize" not in code


def test_exhibit_system_is_shared_by_equity_research_and_executive_brief() -> None:
    exhibits = _code(EXHIBITS_STY)
    equity = _code(EQUITY_STY)
    for primitive in ("exhibit", "fullwidthexhibit", "exhibitgrid", "exhibitpair", "financialtable"):
        assert rf"\NewDocumentEnvironment{{{primitive}}}" in exhibits
        assert rf"\NewDocumentEnvironment{{{primitive}}}" not in equity
    assert r"\NewDocumentCommand{\exhibitpane}" in exhibits
    assert r"\RequirePackage{reportkit-exhibits}" in equity
    # A shared module stays theme- and publication-neutral in code.
    assert "institutional" not in exhibits
    assert "executive" not in exhibits
    assert r"\definecolor" not in exhibits


def test_every_type_scale_token_the_shared_modules_use_is_defined_by_both_themes() -> None:
    used = set(re.findall(r"\\(rk[a-z]+size)\b", _code(EXHIBITS_STY) + _code(BRIEF_STY)))
    assert {"rkexhibitheadlinesize", "rktablebodysize", "rkheadlinesize", "rkdecksize"} <= used
    executive = _code(EXECUTIVE_PAGED)
    institutional = _code(INSTITUTIONAL_COMMON)
    for token in sorted(used):
        assert rf"\newcommand{{\{token}}}" in executive, token
        assert rf"\newcommand{{\{token}}}" in institutional, token


def test_executive_paged_adapter_owns_only_renderer_specific_values() -> None:
    code = _code(EXECUTIVE_PAGED)
    assert r"\geometry{letterpaper" in code
    assert r"\definecolor" not in code
    assert "RKTokCallout" not in code and "RKTokMetric" not in code


def test_primitive_availability_follows_the_packages_that_load_them() -> None:
    primitives = generate_registry(REPO)["primitives"]
    exhibit = primitives["composition"]["exhibit"]["available_in"]
    assert exhibit["publication_types"] == ["equity-research", "executive-brief"]
    assert exhibit["themes"] == ["executive", "institutional-research"]
    brief = primitives["composition"]["briefheader"]["available_in"]
    assert brief == {"publication_types": ["executive-brief"], "themes": ["executive", "institutional-research"], "renderers": ["paged"]}
    assert primitives["composition"]["researchfrontpage"]["available_in"]["publication_types"] == ["equity-research"]


def test_fixture_covers_the_required_brief_structure_under_both_themes() -> None:
    body = (EXAMPLE / "brief.tex").read_text(encoding="utf-8")
    for section in REQUIRED_SECTIONS:
        assert rf"\section{{{section}}}" in body
    for primitive in (r"\begin{briefheader}", r"\briefmeta", r"\begin{decisionpoint}", r"\begin{metric}",
                      r"\begin{exhibit}", r"\begin{exhibitpair}", r"\begin{financialtable}", r"\begin{redflag}",
                      r"\begin{briefactions}", r"\briefaction", r"\begin{briefsources}"):
        assert primitive in body, primitive
    assert r"\documentclass" not in body
    for theme, name in FIXTURES.items():
        wrapper = (EXAMPLE / name).read_text(encoding="utf-8")
        assert rf"\documentclass[theme={theme},publication-type=executive-brief]{{reportkit}}" in wrapper
        assert r"\input{brief.tex}" in wrapper
        # Wrappers carry identity and theme setup only; the brief itself is shared.
        assert r"\section" not in wrapper and r"\begin{brief" not in wrapper


def _compile_fixture(tmp_path: Path, fixture: str) -> tuple[Path, str]:
    for source in [*TEMPLATES.glob("*.cls"), *TEMPLATES.glob("*.def"), *TEMPLATES.glob("reportkit-*.tex"),
                   *TEMPLATES.glob("*.sty"), *(TEMPLATES / "themes").glob("*.sty"), *PUBLICATION_TYPES_DIR.glob("*.sty")]:
        shutil.copy(source, tmp_path / source.name)
    for source in EXAMPLE.glob("*.tex"):
        shutil.copy(source, tmp_path / source.name)
    fonts = tmp_path / "font_data"
    fonts.mkdir()
    for source in (REPO / "font_data").glob("GoogleSans-*.ttf"):
        shutil.copy(source, fonts / source.name)
    env = dict(os.environ, LC_ALL="C")
    for _ in range(2):
        process = subprocess.run(
            ["lualatex", "-file-line-error", "-interaction=nonstopmode", "-halt-on-error", fixture],
            cwd=tmp_path, env=env, capture_output=True, text=True, timeout=240,
        )
        assert process.returncode == 0, (process.stdout + process.stderr)[-4000:]
    log = (tmp_path / fixture.replace(".tex", ".log")).read_text(encoding="utf-8", errors="replace")
    return tmp_path / fixture.replace(".tex", ".pdf"), log


@requires_lualatex
@pytest.mark.parametrize("theme", sorted(FIXTURES))
def test_acceptance_fixture_compiles_to_a_two_to_eight_page_letter_brief(tmp_path: Path, theme: str) -> None:
    pymupdf = pytest.importorskip("pymupdf")
    pdf, log = _compile_fixture(tmp_path, FIXTURES[theme])
    assert "Overfull \\hbox" not in log
    assert "Overfull \\vbox" not in log
    assert "There were undefined references" not in log
    doc = pymupdf.open(pdf)
    assert 2 <= doc.page_count <= 8
    for page in doc:
        assert round(page.rect.width) == 612 and round(page.rect.height) == 792
    text = "\n".join(page.get_text() for page in doc)
    for section in REQUIRED_SECTIONS:
        assert section in text
    for expected in ("DECISION POINT", "RED FLAG", "Exhibit 1", "Exhibit 3", "ACTION", "OWNER", "DUE", "DECISION OWNER"):
        assert expected in text, expected


@requires_lualatex
def test_latex_rejects_executive_brief_under_an_unregistered_theme(tmp_path: Path) -> None:
    source = tmp_path / "invalid.tex"
    source.write_text(
        "\\documentclass[theme=default,publication-type=executive-brief]{reportkit}\n"
        "\\begin{document}This must not build.\\end{document}\n",
        encoding="utf-8",
    )
    env = dict(os.environ, LC_ALL="C", TEXINPUTS=f"{TEMPLATES}:{TEMPLATES / 'themes'}:{PUBLICATION_TYPES_DIR}:")
    result = subprocess.run(
        ["lualatex", "-interaction=nonstopmode", "-halt-on-error", source.name],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=180,
    )
    assert result.returncode != 0
    assert "Class reportkit Error" in result.stdout + result.stderr
    assert not source.with_suffix(".pdf").exists()


@pytest.mark.skipif(
    any(shutil.which(command) is None for command in ("lualatex", "pandoc")),
    reason="requires a real LuaLaTeX/Pandoc toolchain",
)
@pytest.mark.parametrize("theme", sorted(FIXTURES))
def test_executive_brief_builds_through_the_normal_pipeline(tmp_path: Path, theme: str) -> None:
    source = tmp_path / "publication"
    (source / "manuscript").mkdir(parents=True)
    (source / "fragments").mkdir()
    (source / "publication.yaml").write_text(
        "title: Consolidate the dispatch platforms\n"
        "subtitle: A minimal fixture for the executive-brief pipeline\n"
        "author: ReportKit\n"
        "document:\n"
        "  publication_type: executive-brief\n"
        f"  theme: {theme}\n"
        "  engine: lualatex\n",
        encoding="utf-8",
    )
    (source / "manuscript" / "order.txt").write_text("01-brief.md\n", encoding="utf-8")
    (source / "manuscript" / "01-brief.md").write_text(
        "# Recommendation\n\nApprove the consolidation.\n\n# Risks\n\n- Peak-season cut-over.\n- Planner adoption.\n",
        encoding="utf-8",
    )
    output = tmp_path / "build"
    result = subprocess.run(
        [str(REPO / "reportkit"), "build", "--source-root", str(source), "--output-root", str(output), "--json"],
        capture_output=True, text=True,
    )
    payload = json.loads(result.stdout)
    assert result.returncode == 0, payload
    report = payload["report"]
    assert report["status"] == "passed"
    selection = report["selection"]
    assert selection["publication_type"] == "executive-brief"
    assert selection["theme"] == theme
    assert selection["template"] == "executive-brief.tex"
    assert selection["paper"] == "letter"
    staged = (output / "combined" / "publication.tex").read_text(encoding="utf-8")
    assert rf"\documentclass[theme={theme},publication-type=executive-brief]{{reportkit}}" in staged
    assert r"\begin{briefheader}" in staged
    assert r"\RKContents" not in staged
    # Two short sections flow on one page: the brief switches off long-form
    # page-per-section pagination.
    assert report["page_count"] == 1


def test_pipeline_entrypoint_owns_only_the_class_line_and_brief_front_matter() -> None:
    text = (REPO / "publication_pipeline" / "templates" / "executive-brief.tex").read_text(encoding="utf-8")
    for placeholder in ("%%REPORTKIT_THEME%%", "%%REPORTKIT_PUBLICATION_TYPE%%", "%%REPORTKIT_CLASS%%"):
        assert text.count(placeholder) == 1
    assert text.count(r"\documentclass") == 1
    assert text.count(r"\newcommand{\RKFrontMatter}") == 1
    assert text.count(r"\input{paged-base.tex}") == 1
    assert r"\RKSectionOpensPagefalse" in text
    assert r"\ifRKPubHasCover" in text and r"\ifRKPubIsCombined" in text
    assert r"\begin{briefheader}{\RKPubLeftHeader}{\RKPubTitle}" in text
    for absent in (r"\RKContents", r"\RKTitlePage", r"\input{metadata.tex}", r"\input{body.tex}"):
        assert absent not in text
    longform = (TEMPLATES / "reportkit-longform.sty").read_text(encoding="utf-8")
    assert r"\RKSectionOpensPagetrue" in longform
