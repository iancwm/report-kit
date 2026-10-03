"""Per-publication-type reference and contents skins."""
from __future__ import annotations

from pathlib import Path
import re
import shutil

import pytest

from bibliography_helpers import compile_with_bibliography
from reportkit.publications import PUBLICATION_TYPES

REPO = Path(__file__).resolve().parents[1]
PUBTYPES = REPO / "latex_templates" / "publication_types"
BIB = (
    "@book{smith2024, author={Smith, Ada}, title={Gauges and Rivers}, publisher={Delta Press}, year={2024}}\n"
    "@article{jones2019, author={Jones, Bo}, title={Tidal Survey Methods}, journal={Coastal Notes}, year={2019}}\n"
)
FONT = f"\\setreportkitfontpath{{{REPO / 'font_data'}/}}"
# (publication type, theme, engine, preamble, two section commands, numeric-or-author-year label)
CASES = {
    "book": ("default", "pdflatex", "\\usepackage{reportkit-longform}", "\\section", "Smith (2024)"),
    "feature-article": ("editorial", "lualatex", "\\usepackage{reportkit-longform}", "\\section", "Smith (2024)"),
    "executive-brief": ("executive", "lualatex", "\\usepackage{reportkit-longform}\\RKSectionOpensPagefalse", "\\section", "Smith [1]"),
    "equity-research": ("institutional-research", "lualatex", "\\usepackage{reportkit-longform}" + FONT, "\\section", "Smith (2024)"),
}


def _code(path: Path) -> str:
    return "\n".join(re.sub(r"(?<!\\)%.*$", "", line) for line in path.read_text(encoding="utf-8").splitlines())


# Presentation overrides rendering wholesale with \RKBibRender instead of
# the \RKBibSkinBegin/End hooks, so its skin section starts at that macro.
SKIN_MARKERS = {
    "reportkit-book.sty": "RKBibSkin",
    "reportkit-feature-article.sty": "RKBibSkin",
    "reportkit-executive-brief.sty": "RKBibSkin",
    "reportkit-equity-research.sty": "RKBibSkin",
    "reportkit-presentation.sty": "RKBibRender",
}


@pytest.mark.parametrize("name", list(SKIN_MARKERS))
def test_skins_use_tokens_not_literals(name: str) -> None:
    code = _code(PUBTYPES / name)
    marker = SKIN_MARKERS[name]
    skin = code[code.find(marker) - 200:] if marker in code else ""
    assert skin, f"{name} defines no bibliography skin"
    assert "\\fontsize" not in skin and "\\definecolor" not in skin


@pytest.mark.parametrize("publication_type", list(CASES))
def test_contents_titles_match_registry(publication_type: str) -> None:
    code = _code(PUBTYPES / f"reportkit-{publication_type}.sty")
    title = PUBLICATION_TYPES[publication_type]["contents_title"]
    assert f"\\newcommand{{\\RKContentsTitle}}{{{title}}}" in code


@pytest.mark.parametrize("publication_type", list(CASES))
def test_skin_compiles_with_title_contents_and_labels(tmp_path: Path, publication_type: str) -> None:
    theme, engine, preamble, sectioning, label = CASES[publication_type]
    if shutil.which(engine) is None or shutil.which("bibtex") is None:
        pytest.skip(f"requires {engine} and bibtex")
    style = PUBLICATION_TYPES[publication_type]["bibliography_style"]
    title = PUBLICATION_TYPES[publication_type]["bibliography_title"]
    body = (
        "\\RKContents\n"
        f"{sectioning}{{Findings}}\nAs \\citet{{smith2024}} shows \\citep{{jones2019}}.\n"
        f"{sectioning}{{Outlook}}\nMore text.\n"
        "\\RKBibliography\n"
    )
    result = compile_with_bibliography(
        tmp_path, documentclass=f"\\documentclass[theme={theme},publication-type={publication_type}]{{reportkit}}",
        preamble=preamble, body=body, bib=BIB, style=style, title=title, engine=engine,
    )
    assert result.returncode == 0, result.log[-6000:]
    assert label in result.text
    assert title in result.text
    assert "Gauges and Rivers" in result.text
    contents_title = PUBLICATION_TYPES[publication_type]["contents_title"]
    assert contents_title in result.text
    assert "Findings" in result.text.split(contents_title, 1)[1]
    # The combined log always carries pass-1 "undefined citation" warnings
    # from before bibtex runs; the final pass transcript must be clean.
    final_log = (tmp_path / "doc.log").read_text(encoding="utf-8", errors="replace").lower()
    assert "citation" not in final_log or "undefined" not in final_log


TEN = "".join(
    f"@misc{{ref{i:02d}, author={{Author{i:02d}, A.}}, title={{Entry number {i:02d}}}, year={{2020}}}}\n" for i in range(1, 11)
)
DECK = (
    "\\begin{frame}[plain]\\begin{titleslide}\\end{titleslide}\\end{frame}\n"
    "\\RKContents\n"
    "\\begin{frame}[plain]\\begin{sectiondivider}{Market}\\end{sectiondivider}\\end{frame}\n"
    "\\begin{frame}\\begin{messageslide}{Demand is rising}Per \\citet{ref01}.\\end{messageslide}\\end{frame}\n"
    "\\begin{frame}[plain]\\begin{sectiondivider}{Plan}\\end{sectiondivider}\\end{frame}\n"
    "\\RKBibliography\n"
)


@pytest.mark.skipif(shutil.which("lualatex") is None or shutil.which("bibtex") is None, reason="requires lualatex and bibtex")
def test_presentation_references_paginate_at_eight_and_agenda_lists_sections(tmp_path: Path) -> None:
    result = compile_with_bibliography(
        tmp_path,
        documentclass="\\documentclass[theme=executive,publication-type=presentation]{reportkit-slides}",
        preamble="\\title{Deck}", body=DECK, bib=TEN, include_uncited=True, engine="lualatex",
    )
    assert result.returncode == 0, result.log[-6000:]
    agenda = next(page for page in result.pages if "Agenda" in page)
    assert "Market" in agenda and "Plan" in agenda
    reference_pages = [page for page in result.pages if "Entry number" in page]
    assert len(reference_pages) == 2
    assert "Entry number 08" in reference_pages[0] and "Entry number 09" not in reference_pages[0]
    assert "Entry number 09" in reference_pages[1] and "Entry number 10" in reference_pages[1]
    assert "(cont.)" in reference_pages[1]


def test_agendaslide_contract_and_role() -> None:
    from reportkit.primitive_targets import role_for
    from reportkit.registry import generate_registry

    assert "agendaslide" in generate_registry()["primitives"]["composition"]
    assert role_for("agendaslide", "composition", "presentation") == "native"
