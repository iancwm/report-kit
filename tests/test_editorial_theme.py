"""Phase E contract, fixture and gate coverage for the editorial theme and the
feature-article publication type.

The Phase E gate (implementation plan section 9): "replace the editorial
theme with a test theme and compile the same feature structure unchanged.
No feature primitive may mention editorial." The swap below registers an
unrelated probe theme -- the default theme's common package plus a probe
paged adapter written here, sharing nothing with the editorial files --
through the real generated LaTeX registry, then compiles the canonical
fixture with only its ``theme=`` option changed.
"""
from __future__ import annotations

from collections import Counter
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

import pytest

from reportkit import publications
from reportkit.publications import PUBLICATION_TYPES, THEMES, render_latex_registry, resolve_build_target
from reportkit.registry import generate_registry

REPO = Path(__file__).resolve().parents[1]
TEMPLATES = REPO / "latex_templates"
FEATURE_STY = TEMPLATES / "publication_types" / "reportkit-feature-article.sty"
CORE = TEMPLATES / "reportkit-core.sty"
THEME_STY = TEMPLATES / "themes" / "reportkit-theme-editorial.sty"
ADAPTER_STY = TEMPLATES / "themes" / "reportkit-theme-editorial-paged.sty"
EXAMPLE = TEMPLATES / "examples" / "editorial-feature"
FEATURE_PRIMITIVES = {
    "featureopening", "featureheadline", "featuredeck", "featurebyline", "openingvisual",
    "imagecredit", "dropcap", "featurecolumns", "pullquote", "featuresidebar",
    "featureexhibit", "featuresection", "featurereferences",
}
PROBE_THEME = "feature-probe"

requires_lualatex = pytest.mark.skipif(
    shutil.which("lualatex") is None, reason="the editorial theme requires lualatex",
)


def _code(path: Path) -> str:
    """Source with full-line and trailing TeX comments removed."""
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        lines.append(re.sub(r"(?<!\\)%.*$", "", line))
    return "\n".join(lines)


def _texinputs(*first: Path) -> str:
    paths = [*first, TEMPLATES, TEMPLATES / "themes", TEMPLATES / "publication_types"]
    return ":".join(str(path) for path in paths) + ":"


def _compile(tex: Path, *, texinputs: str | None = None, runs: int = 2) -> subprocess.CompletedProcess:
    env = dict(os.environ, LC_ALL="C", TEXINPUTS=texinputs or _texinputs(tex.parent))
    result = None
    for _ in range(runs):
        result = subprocess.run(
            ["lualatex", "-file-line-error", "-interaction=nonstopmode", "-halt-on-error", tex.name],
            cwd=tex.parent, env=env, capture_output=True, text=True, timeout=300,
        )
        if result.returncode:
            break
    assert result is not None
    return result


def _fonts(pdf: Path) -> set[str]:
    import pymupdf

    with pymupdf.open(pdf) as document:
        return {font[3].split("+", 1)[-1] for page in document for font in page.get_fonts()}


def _body_letters(pdf: Path) -> Counter[str]:
    """Letter multiset of the text block, excluding running heads and feet.

    Line breaks, hyphenation, column breaks and page count legitimately
    differ between themes; the letters the article contains must not. Both
    themes keep their running furniture outside a 23mm band at the top and
    bottom of the page, so clipping to the text block compares content only.
    """
    import pymupdf

    band = 23 * 72 / 25.4
    letters: Counter[str] = Counter()
    with pymupdf.open(pdf) as document:
        for page in document:
            clip = pymupdf.Rect(page.rect.x0, page.rect.y0 + band, page.rect.x1, page.rect.y1 - band)
            letters.update(re.findall(r"[a-z]", page.get_text("text", clip=clip).lower()))
    return letters


# -----------------------------------------------------------------------------
# Registry and theme contract
# -----------------------------------------------------------------------------
def test_feature_article_and_editorial_are_registered_as_a_stable_paged_pair() -> None:
    publication = PUBLICATION_TYPES["feature-article"]
    theme = THEMES["editorial"]
    assert publication["renderer"] == "paged"
    assert publication["themes"] == ["editorial"]
    assert publication["template"] == "feature-article.tex"
    assert publication["package"] == "reportkit-feature-article"
    assert publication["stability"] == theme["stability"] == "stable"
    assert theme["required_engine"] == "lualatex"
    assert theme["renderer_adapters"] == {"paged": "reportkit-theme-editorial-paged"}
    target = resolve_build_target("feature-article", "editorial", repo_root=REPO)
    assert (target.renderer, target.class_name, target.paper, target.engine) == ("paged", "reportkit", "a4", "lualatex")
    for other in ("default", "institutional-research", "executive"):
        with pytest.raises(publications.PublicationRegistryError):
            resolve_build_target("feature-article", other, repo_root=REPO)


def test_editorial_language_coverage_is_declared_honestly() -> None:
    from reportkit.themes import get_theme

    language = THEMES["editorial"]["language_support"]
    assert language["verified"] == ["en"]
    assert language["metadata_only"] == ["vi"]
    assert language["scripts"]["verified"] == ["Latn"]
    assert language["rtl"] == "unsupported"
    coverage = get_theme("editorial").script_coverage
    assert coverage.verified == ("Latn",)
    assert coverage.rtl == "unsupported"


def test_editorial_uses_libertinus_serif_body_with_a_complementary_sans() -> None:
    from reportkit.themes import get_theme

    theme_code = _code(THEME_STY)
    assert r"\RequirePackage{libertinus}" in theme_code
    assert "Libertinus Serif Display" in theme_code
    assert "Libertinus Serif Initials" in theme_code
    typography = get_theme("editorial").typography
    assert typography.body == "Libertinus Serif"
    assert typography.metadata == typography.chart == "Libertinus Sans"
    assert r"\ifPDFTeX" in theme_code  # LuaLaTeX guard, decision D9


def test_editorial_python_theme_matches_latex_palette_and_contract() -> None:
    pytest.importorskip("matplotlib")
    import reportkit_viz as rkv
    from reportkit.themes import get_theme, validate_theme_contract

    theme = get_theme("editorial")
    assert validate_theme_contract(theme) == []
    assert rkv.validate_palette_against_latex(THEME_STY, theme.latex_colors) == []
    assert rkv.validate_theme_contract_against_latex("editorial") == []
    # Geometry derivation mirrors the paged adapter's 30mm/30mm A4 margins.
    assert "left=30mm,right=30mm" in ADAPTER_STY.read_text(encoding="utf-8")
    assert theme.text_width_in == pytest.approx(150 / 25.4)


# -----------------------------------------------------------------------------
# Structure/style boundary
# -----------------------------------------------------------------------------
def test_no_feature_primitive_mentions_editorial() -> None:
    assert "editorial" not in FEATURE_STY.read_text(encoding="utf-8").lower()
    registry = generate_registry(REPO)
    records = {
        name: record
        for kind in registry["primitives"].values()
        for name, record in kind.items()
        if record["source"]["file"].endswith("reportkit-feature-article.sty")
    }
    assert set(records) == FEATURE_PRIMITIVES
    for name, record in records.items():
        assert "editorial" not in json.dumps({**record, "available_in": None}).lower(), name


def test_feature_article_owns_structure_only() -> None:
    code = _code(FEATURE_STY)
    for forbidden in (r"\definecolor", r"\fontsize", r"\selectfont", r"\rk@theme", r"\sffamily", r"\rmfamily", r"\bfseries"):
        assert forbidden not in code, forbidden
    # Every color is a feature token, never a palette name.
    for argument in re.findall(r"\\color\{([^}]*)\}", code):
        assert argument.startswith(r"\RKTokFeature"), argument
    assert r"\RKAssertFeatureTokens" in code


def test_feature_tokens_are_declared_used_and_populated_by_the_editorial_adapter() -> None:
    declared = set(re.findall(r"\\newcommand\{\\(RKTokFeature[A-Za-z]+)\}", CORE.read_text(encoding="utf-8")))
    used = set(re.findall(r"\\(RKTokFeature[A-Za-z]+)", _code(FEATURE_STY)))
    populated = set(re.findall(r"\\renewcommand\{\\(RKTokFeature[A-Za-z]+)\}", ADAPTER_STY.read_text(encoding="utf-8")))
    assert declared, "feature token contract missing from reportkit-core.sty"
    assert used == declared, (sorted(used - declared), sorted(declared - used))
    assert populated == declared, sorted(declared ^ populated)
    assert r"\rk@featuretokensloadedtrue" in ADAPTER_STY.read_text(encoding="utf-8")


def test_rhythm_vocabulary_is_closed_not_a_positioning_api() -> None:
    code = _code(FEATURE_STY)
    # featureexhibit's only option key is span, and span accepts exactly
    # column or full; everything else is a hard error.
    keys = re.findall(r"^\s*([a-z]+)/\.code", code, re.MULTILINE)
    assert keys == ["span"]
    assert re.findall(r"\\ifstrequal\{#1\}\{([a-z]+)\}", code) == ["column", "full"]
    assert "FEATURE_EXHIBIT_UNKNOWN_SPAN" in code
    for forbidden in (r"\put(", r"\begin{picture}", "remember picture", "textblock", r"\begin{figure", "wrapfigure"):
        assert forbidden not in code, forbidden


def test_feature_primitives_are_registered_with_examples_and_availability() -> None:
    registry = generate_registry(REPO, strict=True)
    for name in FEATURE_PRIMITIVES:
        kind = "command" if name in {"featureheadline", "featuredeck", "featurebyline", "imagecredit", "dropcap", "pullquote", "featuresection"} else "composition"
        record = registry["primitives"][kind][name]
        assert record["available_in"]["publication_types"] == ["feature-article"]
        assert record["available_in"]["themes"] == ["editorial"]
        assert record["stability"] == "experimental"
        assert record["example"].strip()
        assert record["description"] and record["description"] != name.title()


# -----------------------------------------------------------------------------
# Fixture
# -----------------------------------------------------------------------------
def test_fixture_is_fictional_and_covers_the_required_editorial_elements() -> None:
    source = (EXAMPLE / "report.tex").read_text(encoding="utf-8")
    assert source.splitlines()[0] == r"\documentclass[theme=editorial,publication-type=feature-article]{reportkit}"
    for required in (
        r"\begin{featureopening}", r"\featureheadline", r"\featuredeck", r"\featurebyline",
        r"\begin{openingvisual}", r"\dropcap", r"\featuresection", r"\begin{featurecolumns}",
        r"\pullquote", r"\begin{featuresidebar}", r"\begin{featureexhibit}[span=full]",
        r"\begin{featureexhibit}{", r"\imagecredit", r"\begin{featurereferences}",
    ):
        assert required in source, required
    body = source.split(r"\begin{document}", 1)[1]
    for forbidden in (r"\fontsize", r"\color{", r"\begin{minipage}", r"\vspace", r"\hspace", r"\definecolor"):
        assert forbidden not in body, forbidden
    assert "fictional" in source.lower()
    assert (EXAMPLE / "figures.py").is_file()
    for figure in ("opening-delta", "warning-lead-time", "gauges-by-district"):
        assert (EXAMPLE / "figures" / f"{figure}.pdf").is_file()


@pytest.fixture(scope="module")
def editorial_pdf(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, str]:
    if shutil.which("lualatex") is None:
        pytest.skip("the editorial theme requires lualatex")
    work = tmp_path_factory.mktemp("editorial-feature")
    shutil.copy(EXAMPLE / "report.tex", work / "report.tex")
    shutil.copytree(EXAMPLE / "figures", work / "figures")
    result = _compile(work / "report.tex")
    log = (work / "report.log").read_text(encoding="utf-8", errors="replace") if (work / "report.log").exists() else ""
    assert result.returncode == 0, (result.stdout + result.stderr)[-6000:]
    return work / "report.pdf", log


@requires_lualatex
def test_editorial_fixture_compiles_to_six_to_eight_clean_a4_pages(editorial_pdf: tuple[Path, str]) -> None:
    pymupdf = pytest.importorskip("pymupdf")
    pdf, log = editorial_pdf
    with pymupdf.open(pdf) as document:
        assert 6 <= document.page_count <= 8
        for page in document:
            assert round(page.rect.width * 25.4 / 72) == 210
            assert round(page.rect.height * 25.4 / 72) == 297
            assert page.get_text().strip(), "blank page"
        metadata = document.metadata
        text = " ".join(page.get_text() for page in document)
    assert metadata["title"] == "The river that learned to count"
    assert "Exhibit 1" in text and "Exhibit 2" in text and "Exhibit 3" in text
    assert "Notes and sources" in text
    assert "Overfull" not in log
    assert "There were undefined references" not in log
    assert "Undefined control sequence" not in log
    assert "LaTeX Font Warning" not in log


@requires_lualatex
def test_editorial_fixture_uses_the_declared_type_stack(editorial_pdf: tuple[Path, str]) -> None:
    pytest.importorskip("pymupdf")
    fonts = _fonts(editorial_pdf[0])
    for face in ("LibertinusSerif-Regular", "LibertinusSerif-Italic", "LibertinusSans-Regular",
                 "LibertinusSerifDisplay-Regular", "LibertinusSerifInitials-Regular"):
        assert face in fonts, face


# -----------------------------------------------------------------------------
# The Phase E gate: swap the theme, keep the structure
# -----------------------------------------------------------------------------
PROBE_ADAPTER = r"""\NeedsTeXFormat{LaTeX2e}
\ProvidesPackage{reportkit-theme-featureprobe-paged}[2026/09/23 test-only probe adapter]
% Test-only feature-compatible adapter over the default theme. It shares no
% file or value with the shipped feature theme: sans headlines, no rules, a
% framed sidebar, inset pull quotes, centered credits and plain openings.
\RequirePackage{reportkit-theme-default-paged}
\renewcommand{\RKTokFeatureOpeningPageStyle}{plain}
\renewcommand{\RKTokFeatureOpeningTopSkip}{0pt}
\renewcommand{\RKTokFeatureOpeningRuleColor}{Hairline}
\renewcommand{\RKTokFeatureOpeningRuleWidth}{0pt}
\renewcommand{\RKTokFeatureOpeningAfterSkip}{2mm}
\renewcommand{\RKTokFeatureKickerFont}{\sffamily\small}
\renewcommand{\RKTokFeatureKickerColor}{Muted}
\renewcommand{\RKTokFeatureKickerTransform}{\@firstofone}
\renewcommand{\RKTokFeatureHeadlineFont}{\sffamily\bfseries\LARGE}
\renewcommand{\RKTokFeatureHeadlineColor}{LinkBlue}
\renewcommand{\RKTokFeatureDeckFont}{\sffamily\large}
\renewcommand{\RKTokFeatureDeckColor}{Ink}
\renewcommand{\RKTokFeatureBylineFont}{\sffamily\small\bfseries}
\renewcommand{\RKTokFeatureBylineColor}{Muted}
\renewcommand{\RKTokFeatureElementSkip}{1.5mm}
\renewcommand{\RKTokFeatureCaptionFont}{\small\itshape}
\renewcommand{\RKTokFeatureCaptionColor}{Ink}
\renewcommand{\RKTokFeatureCreditFont}{\footnotesize}
\renewcommand{\RKTokFeatureCreditColor}{Ink}
\renewcommand{\RKTokFeatureCreditAlign}{\centering}
\renewcommand{\RKTokFeaturePullQuoteFont}{\sffamily\bfseries\large}
\renewcommand{\RKTokFeaturePullQuoteColor}{Ink}
\renewcommand{\RKTokFeaturePullQuoteAttributionFont}{\sffamily\footnotesize}
\renewcommand{\RKTokFeaturePullQuoteRuleColor}{Hairline}
\renewcommand{\RKTokFeaturePullQuoteRuleWidth}{0pt}
\renewcommand{\RKTokFeaturePullQuoteInset}{6mm}
\renewcommand{\RKTokFeaturePullQuoteSkip}{2mm}
\renewcommand{\RKTokFeatureSidebarTitleFont}{\sffamily\bfseries}
\renewcommand{\RKTokFeatureSidebarTitleColor}{LinkBlue}
\renewcommand{\RKTokFeatureSidebarBodyFont}{\small}
\renewcommand{\RKTokFeatureSidebarFill}{white}
\renewcommand{\RKTokFeatureSidebarRuleColor}{LinkBlue}
\renewcommand{\RKTokFeatureSidebarRuleWidth}{.6pt}
\renewcommand{\RKTokFeatureSidebarAccentRuleWidth}{.6pt}
\renewcommand{\RKTokFeatureSidebarPad}{2mm}
\renewcommand{\RKTokFeatureExhibitLabelFont}{\sffamily\footnotesize}
\renewcommand{\RKTokFeatureExhibitLabelColor}{Muted}
\renewcommand{\RKTokFeatureExhibitTitleFont}{\sffamily\bfseries}
\renewcommand{\RKTokFeatureExhibitTitleColor}{Ink}
\renewcommand{\RKTokFeatureExhibitRuleColor}{Hairline}
\renewcommand{\RKTokFeatureExhibitRuleWidth}{0pt}
\renewcommand{\RKTokFeatureExhibitInsetFraction}{1}
\renewcommand{\RKTokFeatureExhibitSkip}{2mm}
\renewcommand{\RKTokFeatureSectionFont}{\sffamily\bfseries\Large}
\renewcommand{\RKTokFeatureSectionColor}{LinkBlue}
\renewcommand{\RKTokFeatureSectionRuleColor}{Hairline}
\renewcommand{\RKTokFeatureSectionRuleWidth}{0pt}
\renewcommand{\RKTokFeatureStandfirstFont}{\sffamily}
\renewcommand{\RKTokFeatureStandfirstColor}{Muted}
\renewcommand{\RKTokFeatureSectionSkip}{3mm}
\renewcommand{\RKTokFeatureColumnGutter}{5mm}
\renewcommand{\RKTokFeatureColumnRuleWidth}{0pt}
\renewcommand{\RKTokFeatureColumnRuleColor}{Hairline}
\renewcommand{\RKTokFeatureDropCapFont}{\sffamily\bfseries}
\renewcommand{\RKTokFeatureDropCapColor}{LinkBlue}
\renewcommand{\RKTokFeatureDropCapLeadFont}{\bfseries}
\renewcommand{\RKTokFeatureDropCapLines}{2}
\renewcommand{\RKTokFeatureReferenceTitleFont}{\sffamily\bfseries}
\renewcommand{\RKTokFeatureReferenceFont}{\small}
\renewcommand{\RKTokFeatureReferenceColor}{Ink}
\rk@featuretokensloadedtrue
\endinput
"""


def _probe_registry(monkeypatch: pytest.MonkeyPatch) -> str:
    themes = dict(publications.THEMES)
    themes[PROBE_THEME] = publications._theme(
        PROBE_THEME, renderers=["paged"], required_engine="lualatex",
        common_package="reportkit-theme-default", stability="experimental", since="0.0.0",
        renderer_adapters={"paged": "reportkit-theme-featureprobe-paged"},
    )
    publication_types = {name: dict(record) for name, record in publications.PUBLICATION_TYPES.items()}
    publication_types["feature-article"]["themes"] = [*publication_types["feature-article"]["themes"], PROBE_THEME]
    monkeypatch.setattr(publications, "THEMES", themes)
    monkeypatch.setattr(publications, "PUBLICATION_TYPES", publication_types)
    return publications.render_latex_registry()


def test_probe_theme_populates_exactly_the_feature_contract() -> None:
    declared = set(re.findall(r"\\newcommand\{\\(RKTokFeature[A-Za-z]+)\}", CORE.read_text(encoding="utf-8")))
    populated = set(re.findall(r"\\renewcommand\{\\(RKTokFeature[A-Za-z]+)\}", PROBE_ADAPTER))
    assert populated == declared
    assert "editorial" not in PROBE_ADAPTER.lower()


@requires_lualatex
def test_gate_same_feature_structure_compiles_unchanged_under_a_probe_theme(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, editorial_pdf: tuple[Path, str],
) -> None:
    pytest.importorskip("pymupdf")
    registry = _probe_registry(monkeypatch)
    assert render_latex_registry() == registry  # the real generator, not a hand edit
    assert rf"\DeclareOption{{theme={PROBE_THEME}}}" in registry
    (tmp_path / "reportkit-publication-registry.def").write_text(registry, encoding="utf-8")
    (tmp_path / "reportkit-theme-featureprobe-paged.sty").write_text(PROBE_ADAPTER, encoding="utf-8")

    original = (EXAMPLE / "report.tex").read_text(encoding="utf-8")
    swapped = original.replace("theme=editorial,", f"theme={PROBE_THEME},", 1)
    assert swapped != original
    # Only the \documentclass option changes; the whole feature structure is
    # byte-identical.
    assert swapped.splitlines()[1:] == original.splitlines()[1:]
    (tmp_path / "report.tex").write_text(swapped, encoding="utf-8")
    shutil.copytree(EXAMPLE / "figures", tmp_path / "figures")

    result = _compile(tmp_path / "report.tex", texinputs=_texinputs(tmp_path))
    assert result.returncode == 0, (result.stdout + result.stderr)[-6000:]
    probe_pdf = tmp_path / "report.pdf"
    log = (tmp_path / "report.log").read_text(encoding="utf-8", errors="replace")
    assert "reportkit-theme-featureprobe-paged" in log
    assert "reportkit-theme-editorial" not in log

    editorial_fonts = _fonts(editorial_pdf[0])
    probe_fonts = _fonts(probe_pdf)
    # Materially different appearance: the probe never loads the editorial
    # display or initials faces.
    assert "LibertinusSerifDisplay-Regular" in editorial_fonts
    assert "LibertinusSerifDisplay-Regular" not in probe_fonts
    assert "LibertinusSerifInitials-Regular" not in probe_fonts
    # Same content: every letter of the article survives the swap (the kicker
    # case transform differs by design, so compare case-insensitively).
    editorial_letters = _body_letters(editorial_pdf[0])
    probe_letters = _body_letters(probe_pdf)
    assert sum(editorial_letters.values()) > 10000
    assert editorial_letters == probe_letters, (editorial_letters - probe_letters, probe_letters - editorial_letters)


# -----------------------------------------------------------------------------
# Primitive examples and rhythm failures
# -----------------------------------------------------------------------------
def _feature_document(body: str) -> str:
    return (
        "\\documentclass[theme=editorial,publication-type=feature-article]{reportkit}\n"
        "\\title{Feature primitive smoke}\n\\begin{document}\n" + body + "\n\\end{document}\n"
    )


@requires_lualatex
def test_every_registered_feature_example_compiles_under_editorial(tmp_path: Path) -> None:
    registry = generate_registry(REPO, strict=True)
    examples = [
        record["example"]
        for kind in registry["primitives"].values()
        for name, record in sorted(kind.items())
        if name in FEATURE_PRIMITIVES
    ]
    assert len(examples) == len(FEATURE_PRIMITIVES)
    tex = tmp_path / "examples.tex"
    tex.write_text(_feature_document("\n\n".join(examples)), encoding="utf-8")
    result = _compile(tex, runs=1)
    assert result.returncode == 0, (result.stdout + result.stderr)[-6000:]


@requires_lualatex
@pytest.mark.parametrize(
    ("body", "diagnostic"),
    (
        ("\\begin{featurecolumns}\n\\begin{featureexhibit}[span=full]{Too wide}\nx\n\\end{featureexhibit}\n\\end{featurecolumns}",
         "FEATURE_EXHIBIT_FULL_SPAN_IN_COLUMNS"),
        ("\\begin{featurecolumns}\n\\begin{openingvisual}{Caption}\nx\n\\end{openingvisual}\n\\end{featurecolumns}",
         "FEATURE_OPENING_VISUAL_IN_COLUMNS"),
        ("\\begin{featurecolumns}\n\\begin{featurecolumns}\nx\n\\end{featurecolumns}\n\\end{featurecolumns}",
         "FEATURE_COLUMNS_NESTED"),
        ("\\begin{featureexhibit}[span=left]{No free placement}\nx\n\\end{featureexhibit}",
         "FEATURE_EXHIBIT_UNKNOWN_SPAN"),
    ),
)
def test_rhythm_misuse_fails_loudly(tmp_path: Path, body: str, diagnostic: str) -> None:
    tex = tmp_path / "misuse.tex"
    tex.write_text(_feature_document(body), encoding="utf-8")
    result = _compile(tex, runs=1)
    assert result.returncode != 0
    log = tex.with_suffix(".log").read_text(encoding="utf-8", errors="replace")
    assert diagnostic in log
    assert not tex.with_suffix(".pdf").exists()


@requires_lualatex
def test_feature_article_without_feature_tokens_fails_at_load(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A theme that has not populated the feature contract cannot silently
    render a feature article with another theme's values."""
    themes = dict(publications.THEMES)
    publication_types = {name: dict(record) for name, record in publications.PUBLICATION_TYPES.items()}
    publication_types["feature-article"]["themes"] = ["editorial", "default"]
    monkeypatch.setattr(publications, "THEMES", themes)
    monkeypatch.setattr(publications, "PUBLICATION_TYPES", publication_types)
    (tmp_path / "reportkit-publication-registry.def").write_text(publications.render_latex_registry(), encoding="utf-8")
    tex = tmp_path / "untokened.tex"
    tex.write_text(_feature_document("x").replace("theme=editorial", "theme=default"), encoding="utf-8")
    result = _compile(tex, texinputs=_texinputs(tmp_path), runs=1)
    assert result.returncode != 0
    # TeX wraps terminal lines at 79 columns, so join them before matching.
    assert "feature-composition style tokens" in (result.stdout + result.stderr).replace("\n", "")


# -----------------------------------------------------------------------------
# Pipeline
# -----------------------------------------------------------------------------
@pytest.mark.skipif(
    any(shutil.which(command) is None for command in ("lualatex", "pandoc")),
    reason="the editorial theme requires lualatex and the pipeline requires pandoc",
)
def test_feature_article_builds_through_the_normal_pipeline(tmp_path: Path) -> None:
    source = tmp_path / "publication"
    (source / "manuscript").mkdir(parents=True)
    (source / "fragments").mkdir()
    (source / "publication.yaml").write_text(
        "title: The river that learned to count\n"
        "subtitle: A fictional feature for the pipeline smoke test\n"
        "author: ReportKit\n"
        "document:\n"
        "  publication_type: feature-article\n"
        "  theme: editorial\n"
        "  engine: lualatex\n",
        encoding="utf-8",
    )
    (source / "manuscript" / "order.txt").write_text("01-feature.md\n", encoding="utf-8")
    (source / "manuscript" / "01-feature.md").write_text(
        "# Counting the water\n\nPlain Markdown prose in a feature article.\n\n"
        "## A second movement\n\nMore prose.\n",
        encoding="utf-8",
    )
    output = tmp_path / "build"
    result = subprocess.run(
        [str(REPO / "reportkit"), "build", "--source-root", str(source), "--output-root", str(output), "--json"],
        capture_output=True, text=True,
    )
    payload = json.loads(result.stdout)
    assert result.returncode == 0, payload
    selection = payload["report"]["selection"]
    assert selection["publication_type"] == "feature-article"
    assert selection["theme"] == "editorial"
    assert selection["template"] == "feature-article.tex"
    assert selection["engine"] == "lualatex"
    staged = (output / "combined" / "publication.tex").read_text(encoding="utf-8")
    assert r"\documentclass[theme=editorial,publication-type=feature-article]{reportkit}" in staged
