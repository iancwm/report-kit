"""Engine-wide bibliography and contents packages."""
from __future__ import annotations

from pathlib import Path
import shutil

import pytest

from bibliography_helpers import compile_with_bibliography
from reportkit.primitive_targets import role_for
from reportkit.registry import generate_registry

pytestmark = pytest.mark.skipif(
    shutil.which("pdflatex") is None or shutil.which("bibtex") is None, reason="requires pdflatex and bibtex",
)

BIB = (
    "@book{smith2024, author={Smith, Ada}, title={{Gauges and Rivers}}, publisher={Delta Press}, year={2024}}\n"
    "@article{jones2019, author={Jones, Bo}, title={{Tidal Survey Methods}}, journal={Coastal Notes}, year={2019}, volume={4}, pages={1--9}}\n"
    "@misc{lee2020, author={Lee, Cy}, title={{Uncited Field Notes}}, year={2020}}\n"
)
BODY = (
    "\\usepackage{reportkit-longform}\n" "\\RKContents\n"
    "\\section{Findings}\nAs \\citet{smith2024} shows, gauges matter \\citep{jones2019}.\n"
    "\\RKBibliography\n"
)


def _body() -> tuple[str, str]:
    preamble, body = BODY.split("\n", 1)
    return preamble, body


def test_numeric_style_formats_labels_and_lists_only_cited(tmp_path: Path) -> None:
    preamble, body = _body()
    result = compile_with_bibliography(tmp_path, documentclass="\\documentclass{reportkit}", preamble=preamble, body=body, bib=BIB)
    assert result.returncode == 0, result.log[-4000:]
    assert result.passes == 3
    assert "Smith [1]" in result.text
    assert "[2]" in result.text
    assert "Gauges and Rivers" in result.text and "Tidal Survey Methods" in result.text
    assert "Uncited Field Notes" not in result.text
    assert "References" in result.text
    assert "[?" not in result.text


def test_author_year_style_formats_labels(tmp_path: Path) -> None:
    preamble, body = _body()
    result = compile_with_bibliography(
        tmp_path, documentclass="\\documentclass{reportkit}", preamble=preamble, body=body, bib=BIB, style="author-year",
    )
    assert result.returncode == 0, result.log[-4000:]
    assert "Smith (2024)" in result.text
    assert "(Jones, 2019)" in result.text


def test_include_uncited_lists_every_entry(tmp_path: Path) -> None:
    preamble, body = _body()
    result = compile_with_bibliography(
        tmp_path, documentclass="\\documentclass{reportkit}", preamble=preamble, body=body, bib=BIB, include_uncited=True,
    )
    assert result.returncode == 0, result.log[-4000:]
    assert "Uncited Field Notes" in result.text


def test_default_contents_page_lists_references_section(tmp_path: Path) -> None:
    preamble, body = _body()
    result = compile_with_bibliography(tmp_path, documentclass="\\documentclass{reportkit}", preamble=preamble, body=body, bib=BIB)
    assert result.returncode == 0, result.log[-4000:]
    contents_page = next(
        page for page in result.pages
        if "Findings" in page and "References" in page and "Gauges" not in page
    )
    assert "Contents" in contents_page


def test_unconfigured_document_does_not_load_natbib(tmp_path: Path) -> None:
    preamble = "\\usepackage{reportkit-longform}"
    body = "\\RKContents\n\\section{Only}\nText.\n"
    result = compile_with_bibliography(tmp_path, documentclass="\\documentclass{reportkit}", preamble=preamble, body=body, bib=None)
    assert result.returncode == 0, result.log[-4000:]
    assert result.passes == 2
    assert "natbib.sty" not in (tmp_path / "doc.log").read_text(encoding="utf-8", errors="replace")


def test_manual_bookreferences_still_compile_without_configuration(tmp_path: Path) -> None:
    body = (
        "\\section{Body}\nSee \\cite{x}.\n"
        "\\begin{bookreferences}{9}\n\\bibitem{x} Example Author. A fictional source. 2026.\n\\end{bookreferences}\n"
    )
    result = compile_with_bibliography(
        tmp_path, documentclass="\\documentclass[publication-type=book]{reportkit}", body=body, bib=None,
    )
    assert result.returncode == 0, result.log[-4000:]
    assert "A fictional source" in result.text


def test_rkbibliography_without_configuration_is_a_coded_error(tmp_path: Path) -> None:
    result = compile_with_bibliography(tmp_path, documentclass="\\documentclass{reportkit}", body="\\RKBibliography", bib=None)
    assert result.returncode != 0
    assert "RK_BIBLIOGRAPHY_UNCONFIGURED" in result.log


def test_contract_records_and_roles() -> None:
    registry = generate_registry()
    commands = registry["primitives"]["command"]
    assert "RKBibliography" in commands and "RKContents" in commands
    for publication_type in ("technical-report", "book", "feature-article", "executive-brief", "equity-research", "presentation"):
        assert role_for("RKBibliography", "command", publication_type) == "native"
        assert role_for("RKContents", "command", publication_type) == "native"
