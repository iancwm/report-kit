"""Phase F2 coverage for the book publication type.

Registry shape, the structure/style boundary (every visual value is a
book-composition token populated by the theme's paged adapter), the deferred
print-production scope, the canonical fixture under default (shared with the
technical alias) and the editorial compatibility smoke, LaTeX-side rejection,
and the Markdown pipeline entrypoint.
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
from reportkit.publications import (
    PUBLICATION_TYPES,
    PublicationRegistryError,
    check_publication_registry,
    resolve_build_target,
)
from reportkit.registry import generate_registry

REPO = Path(__file__).resolve().parents[1]
TEMPLATES = REPO / "latex_templates"
BOOK_STY = TEMPLATES / "publication_types" / "reportkit-book.sty"
CORE = TEMPLATES / "reportkit-core.sty"
ADAPTERS = {
    "default": TEMPLATES / "themes" / "reportkit-theme-default-paged.sty",
    "editorial": TEMPLATES / "themes" / "reportkit-theme-editorial-paged.sty",
}
EXAMPLE = TEMPLATES / "examples" / "book"
ENTRYPOINT = REPO / "publication_pipeline" / "templates" / "book.tex"
FIXTURES = {"default": ("report.tex", "pdflatex"), "editorial": ("report-editorial.tex", "lualatex")}
BOOK_PRIMITIVES = {
    "bookpart": "command", "bookdetails": "composition", "bookdetail": "command",
    "bookappendix": "command", "bookreferences": "composition", "bookglossary": "composition",
    "glossaryterm": "command",
}


def _code(path: Path | str) -> str:
    """TeX source with comments removed."""
    text = path.read_text(encoding="utf-8") if isinstance(path, Path) else path
    return "\n".join(re.sub(r"(?<!\\)%.*$", "", line) for line in text.splitlines())


def _texinputs(*first: Path) -> str:
    paths = [*first, TEMPLATES, TEMPLATES / "themes", TEMPLATES / "publication_types"]
    return ":".join(str(path) for path in paths) + ":"


def _compile(tex: Path, engine: str, *, texinputs: str | None = None, runs: int = 2) -> subprocess.CompletedProcess:
    env = dict(os.environ, LC_ALL="C", TEXINPUTS=texinputs or _texinputs(tex.parent))
    result = None
    for _ in range(runs):
        result = subprocess.run(
            [engine, "-file-line-error", "-interaction=nonstopmode", "-halt-on-error", tex.name],
            cwd=tex.parent, env=env, capture_output=True, text=True, timeout=300,
        )
        if result.returncode:
            break
    assert result is not None
    return result


def _letters(pdf: Path) -> Counter[str]:
    """Letter multiset of the text block, excluding running heads and feet.

    The opening-page style (title page, part openers, publication details)
    is itself a book-composition token (``RKTokBookOpeningPageStyle``): the
    default theme's "empty" style omits the footer there while editorial's
    "rkeditorialopening" keeps it, so raw whole-page text differs by design
    even though every semantic element renders identically. Clipping to a
    23mm-inset band, the same convention test_editorial_theme.py uses,
    compares body content only.
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
# Registry
# -----------------------------------------------------------------------------
def test_book_is_registered_for_default_technical_and_editorial_only() -> None:
    record = PUBLICATION_TYPES["book"]
    assert record["renderer"] == "paged"
    assert record["paper"] == "a4"
    assert record["themes"] == ["default", "technical", "editorial"]
    assert record["default_target"] == {"theme": "default", "paper": "a4"}
    assert record["template"] == "book.tex"
    assert record["package"] == "reportkit-book"
    assert record["stability"] == "experimental"
    assert check_publication_registry(REPO) == []
    for theme in ("institutional-research", "executive", "venture"):
        with pytest.raises(PublicationRegistryError) as error:
            resolve_build_target("book", theme, repo_root=REPO)
        assert error.value.diagnostic["candidates"] == ["default", "editorial", "technical"]


def test_book_targets_use_the_paged_class_and_each_themes_engine() -> None:
    default = resolve_build_target("book", "default", repo_root=REPO)
    technical = resolve_build_target("book", "technical", repo_root=REPO)
    editorial = resolve_build_target("book", "editorial", repo_root=REPO)
    for target in (default, technical, editorial):
        assert (target.renderer, target.class_name, target.template, target.paper) == ("paged", "reportkit", "book.tex", "a4")
        assert target.publication_package == "reportkit-book"
    assert (default.engine, editorial.engine) == ("pdflatex", "lualatex")
    # The alias pair is one visual target: only the requested name differs.
    assert technical.theme == "default" and technical.alias_of == "default"
    assert technical.as_dict() | {"requested_theme": "default", "requested_name": "default", "alias_of": None} == default.as_dict()
    assert editorial.renderer_adapter == "reportkit-theme-editorial-paged"


# -----------------------------------------------------------------------------
# Scope and the structure/style boundary
# -----------------------------------------------------------------------------
def test_book_reuses_the_paged_renderer_and_defers_print_production() -> None:
    assert not list(TEMPLATES.rglob("reportkit-book.cls"))
    assert set(publications.RENDERERS) == {"paged", "slides"}
    code = _code(BOOK_STY)
    assert r"\RequirePackage{reportkit-longform}" in code
    for deferred in ("twoside", r"\cleardoublepage", "openright", "makeidx", "imakeidx", r"\printindex",
                     "crop", "bleed", "trim", r"\documentclass", r"\LoadClass"):
        assert deferred not in code, deferred
    # Title page, contents and front/main matter come from reportkit-longform.
    for reused in (r"\RKTitlePage", r"\RKContents", r"\RKFrontMatterBegin", r"\RKMainMatterBegin"):
        assert rf"\newcommand{{{reused}}}" not in code and rf"\NewDocumentCommand{{{reused}}}" not in code


def test_book_package_owns_structure_only() -> None:
    code = _code(BOOK_STY)
    for forbidden in (r"\definecolor", r"\fontsize", r"\selectfont", r"\rk@theme", r"\sffamily",
                      r"\rmfamily", r"\bfseries", r"\itshape", r"\large", r"\Large"):
        assert forbidden not in code, forbidden
    for argument in re.findall(r"\\color\{([^}]*)\}", code):
        assert argument.startswith(r"\RKTokBook"), argument
    for theme in ("default", "editorial", "technical", "institutional", "executive", "venture"):
        assert theme not in code.lower(), theme
    assert r"\RKAssertBookTokens" in code
    declared = set(re.findall(r"\\NewDocument(?:Environment|Command)\{\\?([A-Za-z@]+)\}", code))
    assert {name for name in declared if "@" not in name} == set(BOOK_PRIMITIVES)


def test_book_tokens_are_declared_used_and_populated_by_both_canonical_adapters() -> None:
    declared = set(re.findall(r"\\newcommand\{\\(RKTokBook[A-Za-z]+)\}", CORE.read_text(encoding="utf-8")))
    used = set(re.findall(r"\\(RKTokBook[A-Za-z]+)", _code(BOOK_STY)))
    assert declared, "book token contract missing from reportkit-core.sty"
    assert used == declared, (sorted(used - declared), sorted(declared - used))
    for theme, adapter in ADAPTERS.items():
        text = adapter.read_text(encoding="utf-8")
        populated = set(re.findall(r"\\renewcommand\{\\(RKTokBook[A-Za-z]+)\}", text))
        assert populated == declared, (theme, sorted(declared ^ populated))
        assert r"\rk@booktokensloadedtrue" in text


def test_book_primitives_are_registered_with_examples_and_availability() -> None:
    registry = generate_registry(REPO, strict=True)
    for name, kind in BOOK_PRIMITIVES.items():
        record = registry["primitives"][kind][name]
        assert record["available_in"] == {
            "publication_types": ["book"], "themes": ["default", "editorial", "technical"], "renderers": ["paged"],
        }
        assert record["stability"] == "experimental"
        assert record["example"].strip()
        assert record["description"] and record["description"] != name.title()


# -----------------------------------------------------------------------------
# Fixture
# -----------------------------------------------------------------------------
def test_fixture_is_fictional_and_exercises_every_book_structure() -> None:
    body = (EXAMPLE / "book-body.tex").read_text(encoding="utf-8")
    for required in (
        r"\RKFrontMatterBegin", r"\RKTitlePage", r"\begin{bookdetails}", r"\bookdetail", r"\RKContents",
        r"\RKMainMatterBegin", r"\bookpart", r"\section", r"\bookappendix", r"\begin{bookglossary}",
        r"\glossaryterm", r"\begin{bookreferences}", r"\bibitem", r"\cite{", r"\ref{",
    ):
        assert required in body, required
    for forbidden in (r"\documentclass", r"\fontsize", r"\color{", r"\vspace", r"\hspace", r"\definecolor", r"\newpage"):
        assert forbidden not in body, forbidden
    assert "fictional" in body.lower()
    for theme, (name, _) in FIXTURES.items():
        wrapper = (EXAMPLE / name).read_text(encoding="utf-8")
        assert rf"\documentclass[theme={theme},publication-type=book]{{reportkit}}" in wrapper
        assert r"\input{book-body.tex}" in wrapper
        assert r"\section" not in wrapper and r"\book" not in wrapper.replace(r"\input{book-body.tex}", "")


@pytest.fixture(scope="module")
def book_pdfs(tmp_path_factory: pytest.TempPathFactory) -> dict[str, tuple[Path, str]]:
    """Compile the canonical fixture once per theme it is registered for.

    ``technical`` is compiled from the same body with only its class option
    changed: the alias pair shares one visual fixture.
    """
    if shutil.which("pdflatex") is None or shutil.which("lualatex") is None:
        pytest.skip("requires pdflatex and lualatex")
    outputs: dict[str, tuple[Path, str]] = {}
    wrappers = {**{theme: value for theme, value in FIXTURES.items()}, "technical": ("report-technical.tex", "pdflatex")}
    for theme, (name, engine) in wrappers.items():
        work = tmp_path_factory.mktemp(f"book-{theme}")
        shutil.copy(EXAMPLE / "book-body.tex", work / "book-body.tex")
        if theme == "technical":
            source = (EXAMPLE / "report.tex").read_text(encoding="utf-8")
            swapped = source.replace("theme=default,", "theme=technical,", 1)
            assert swapped != source
            (work / name).write_text(swapped, encoding="utf-8")
        else:
            shutil.copy(EXAMPLE / name, work / name)
        result = _compile(work / name, engine)
        assert result.returncode == 0, (result.stdout + result.stderr)[-6000:]
        pdf = work / name.replace(".tex", ".pdf")
        outputs[theme] = (pdf, pdf.with_suffix(".log").read_text(encoding="utf-8", errors="replace"))
    return outputs


@pytest.mark.parametrize("theme", ("default", "editorial"))
def test_fixture_compiles_to_a_clean_a4_book(book_pdfs: dict[str, tuple[Path, str]], theme: str) -> None:
    pymupdf = pytest.importorskip("pymupdf")
    pdf, log = book_pdfs[theme]
    for problem in ("Overfull", "There were undefined references", "Undefined control sequence",
                    "Missing character", "Rerun to get cross-references right"):
        assert problem not in log, problem
    with pymupdf.open(pdf) as document:
        assert 8 <= document.page_count <= 16
        for page in document:
            assert (round(page.rect.width), round(page.rect.height)) == (595, 842)
            assert page.get_text().strip(), "blank page"
        text = "\n".join(page.get_text() for page in document)
        toc = [title for _, title, _ in document.get_toc()]
        assert document.metadata["title"] == "The Quiet Grid"
    for expected in ("PART I", "PART II", "CHAPTER 1", "CHAPTER 3", "APPENDIX A", "Contents", "Glossary",
                     "References", "EDITION", "LICENCE", "Capacity drift", "[1]"):
        assert expected in text, expected
    # Cross-references resolve to chapter and appendix numbers.
    assert "Chapter 2" in text and "Appendix A" in text
    assert toc[:3] == ["Publication details", "Contents", "Part I Foundations"]
    assert toc[-3:] == ["Commissioning checklist", "Glossary", "References"]
    assert "Appendices" in toc


def test_technical_alias_renders_the_same_book_as_default(book_pdfs: dict[str, tuple[Path, str]]) -> None:
    pymupdf = pytest.importorskip("pymupdf")
    default_pdf, _ = book_pdfs["default"]
    technical_pdf, technical_log = book_pdfs["technical"]
    assert "reportkit-theme-default-paged.sty" in technical_log
    with pymupdf.open(default_pdf) as default, pymupdf.open(technical_pdf) as technical:
        assert default.page_count == technical.page_count
        assert [page.get_text() for page in default] == [page.get_text() for page in technical]


def test_editorial_compatibility_smoke_restyles_the_same_book(book_pdfs: dict[str, tuple[Path, str]]) -> None:
    pymupdf = pytest.importorskip("pymupdf")
    default_pdf, default_log = book_pdfs["default"]
    editorial_pdf, editorial_log = book_pdfs["editorial"]
    assert "reportkit-theme-editorial-paged.sty" in editorial_log
    assert "reportkit-theme-default" not in editorial_log
    with pymupdf.open(editorial_pdf) as document:
        fonts = {font[3].split("+", 1)[-1] for page in document for font in page.get_fonts()}
    assert "LibertinusSerifDisplay-Regular" in fonts
    # Same structure and content, different design system: every letter
    # survives the theme change (case-insensitive: labels are transformed).
    assert _letters(default_pdf) == _letters(editorial_pdf)


def test_latex_rejects_book_under_an_unregistered_theme(tmp_path: Path) -> None:
    if shutil.which("lualatex") is None:
        pytest.skip("lualatex not on PATH")
    source = tmp_path / "invalid.tex"
    source.write_text(
        "\\documentclass[theme=institutional-research,publication-type=book]{reportkit}\n"
        "\\begin{document}This must not build.\\end{document}\n",
        encoding="utf-8",
    )
    result = _compile(source, "lualatex", runs=1)
    assert result.returncode != 0
    assert "Class reportkit Error" in result.stdout + result.stderr
    assert not source.with_suffix(".pdf").exists()


def test_book_without_book_tokens_fails_at_load(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A theme that has not populated the book contract cannot silently
    render a book with another theme's values."""
    if shutil.which("lualatex") is None:
        pytest.skip("lualatex not on PATH")
    publication_types = {name: dict(record) for name, record in publications.PUBLICATION_TYPES.items()}
    publication_types["book"]["themes"] = ["default", "technical", "editorial", "executive"]
    monkeypatch.setattr(publications, "PUBLICATION_TYPES", publication_types)
    (tmp_path / "reportkit-publication-registry.def").write_text(publications.render_latex_registry(), encoding="utf-8")
    source = tmp_path / "untokened.tex"
    source.write_text(
        "\\documentclass[theme=executive,publication-type=book]{reportkit}\n"
        "\\begin{document}x\\end{document}\n",
        encoding="utf-8",
    )
    result = _compile(source, "lualatex", texinputs=_texinputs(tmp_path), runs=1)
    assert result.returncode != 0
    assert "book-composition style tokens" in (result.stdout + result.stderr).replace("\n", "")


# -----------------------------------------------------------------------------
# Pipeline
# -----------------------------------------------------------------------------
def test_pipeline_entrypoint_owns_only_the_class_line_and_book_front_matter() -> None:
    text = ENTRYPOINT.read_text(encoding="utf-8")
    for placeholder in ("%%REPORTKIT_THEME%%", "%%REPORTKIT_PUBLICATION_TYPE%%", "%%REPORTKIT_CLASS%%"):
        assert text.count(placeholder) == 1
    assert text.count(r"\documentclass") == 1
    assert text.count(r"\newcommand{\RKFrontMatter}") == 1
    assert text.count(r"\input{paged-base.tex}") == 1
    assert r"\setcounter{secnumdepth}{1}" in text
    for required in (r"\ifRKPubHasCover", r"\ifRKPubIsCombined", r"\RKTitlePage[\RKPubSubtitle]{\RKPubTitle}",
                     r"\begin{bookdetails}", r"\RKContents", r"\RKMainMatterBegin"):
        assert required in text, required
    for absent in (r"\input{metadata.tex}", r"\input{body.tex}", r"\bookpart", r"\bookappendix"):
        assert absent not in text


@pytest.mark.skipif(shutil.which("pandoc") is None, reason="the pipeline requires pandoc")
@pytest.mark.parametrize(("theme", "engine"), (("default", "pdflatex"), ("editorial", "lualatex")))
def test_book_builds_through_the_normal_pipeline(tmp_path: Path, theme: str, engine: str) -> None:
    if shutil.which(engine) is None:
        pytest.skip(f"{engine} not on PATH")
    pymupdf = pytest.importorskip("pymupdf")
    source = tmp_path / "publication"
    (source / "manuscript").mkdir(parents=True)
    (source / "fragments").mkdir()
    (source / "publication.yaml").write_text(
        "title: The Quiet Grid\n"
        "subtitle: A minimal fixture for the book pipeline\n"
        "author: ReportKit\n"
        "document:\n"
        "  publication_type: book\n"
        f"  theme: {theme}\n"
        f"  engine: {engine}\n",
        encoding="utf-8",
    )
    (source / "manuscript" / "order.txt").write_text("01-book.md\n", encoding="utf-8")
    (source / "manuscript" / "01-book.md").write_text(
        "# Why small grids fail quietly\n\nA microgrid rarely fails with a bang.\n\n"
        "## Three kinds of quiet failure\n\n- Capacity drift.\n- Maintenance debt.\n\n"
        "# Measuring load\n\nMeasure before building.\n",
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
    assert (selection["publication_type"], selection["theme"], selection["template"], selection["paper"], selection["engine"]) == (
        "book", theme, "book.tex", "a4", engine,
    )
    staged = (output / "combined" / "publication.tex").read_text(encoding="utf-8")
    assert rf"\documentclass[theme={theme},publication-type=book]{{reportkit}}" in staged
    # Title, publication details, contents, then one page per chapter.
    assert report["page_count"] == 5
    with pymupdf.open(output / "combined" / report["pdf"]) as document:
        text = "\n".join(page.get_text() for page in document)
    assert "CHAPTER 1" in text and "CHAPTER 2" in text and "LICENCE" in text
    # Unset optional identity fields do not produce empty imprint details.
    assert "CLASSIFICATION" not in text and "DISCLAIMER" not in text
