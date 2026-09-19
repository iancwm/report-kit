"""Integration release gate for the four-page algorithm guide spread."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

import pymupdf
import pytest

from geometry import node_rects, word_boxes


REPO = Path(__file__).resolve().parents[1]
TEMPLATES = REPO / "latex_templates"
FIXTURE = TEMPLATES / "examples" / "algorithm_guide_fixture_acceptance_test.tex"


@pytest.fixture
def guide_pdf(tmp_path: Path):
    engine = shutil.which("lualatex")
    if engine is None:
        pytest.skip("lualatex not on PATH")

    source = tmp_path / FIXTURE.name
    shutil.copy2(FIXTURE, source)
    env = dict(
        os.environ,
        LC_ALL="C",
        TEXINPUTS=f"{TEMPLATES}:{TEMPLATES / 'themes'}:{TEMPLATES / 'publication_types'}:",
    )
    logs = []
    for _ in range(2):
        result = subprocess.run(
            [engine, "-file-line-error", "-interaction=nonstopmode", "-halt-on-error", source.name],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            timeout=180,
        )
        logs.append(result.stdout + "\n" + result.stderr)
        assert result.returncode == 0, logs[-1][-5000:]

    pdf = tmp_path / f"{source.stem}.pdf"
    assert pdf.exists()
    return pymupdf.open(pdf), "\n".join(logs)


def test_algorithm_guide_is_four_pages_without_layout_errors(guide_pdf):
    document, log = guide_pdf
    assert len(document) == 4
    assert "Fatal error" not in log
    assert "Undefined control sequence" not in log
    assert "Overfull \\hbox" not in log


def test_algorithm_guide_keeps_sections_and_code_units_together(guide_pdf):
    document, _ = guide_pdf
    page_text = [page.get_text() for page in document]

    assert "Pattern group" in page_text[0]
    assert "TWO POINTERS AND SLIDING WINDOW" in page_text[1]
    assert "STACK AND QUEUE" in page_text[2]
    assert "TOPOLOGICAL SORT" in page_text[3]

    # The title and first source line of every opt-in code unit must remain on
    # the same page. This is the guide-scale contract for keep=auto.
    for title_fragment, first_line in (
        ("Two-pointer", "def pair_sum"),
        ("Window update", "def advance"),
        ("Kahn", "ready = deque"),
    ):
        pages_with_title = [index for index, text in enumerate(page_text) if title_fragment in text]
        pages_with_code = [index for index, text in enumerate(page_text) if first_line in text]
        assert pages_with_title, f"missing code title {title_fragment!r}"
        assert pages_with_code, f"missing code line {first_line!r}"
        assert pages_with_title[0] == pages_with_code[0]


def test_algorithm_guide_ready_queue_matches_zero_indegree_source(guide_pdf):
    document, _ = guide_pdf
    source = FIXTURE.read_text(encoding="utf-8")
    assert r"\dagnode[indegree=0,state=frontier]{clean}" in source
    assert r"\readyqueue{clean}" in source
    assert "zero-indegree badge" in document[3].get_text()


def test_algorithm_guide_index_centers_match_cell_centers(compile_doc):
    # Keep this check description-free so reportkit-diagrams' accessibility
    # ActualText wrapper does not replace the real diagram glyphs in PyMuPDF.
    page = compile_doc(
        r"""
        \begin{diagram}[type=array,width=\textwidth,caption={Guide index geometry.}]
          \begin{arraystate}
            \cell{aa}\cell{bb}\cell{cc}\cell{dd}\cell{ee}
          \end{arraystate}
        \end{diagram}
        """
    )[0]
    cells = [rect for rect in node_rects(page, min_width=10.0) if rect.width < 100]
    boxes = word_boxes(page, {"0", "1", "2", "3", "4"})
    assert len(cells) >= 5
    assert {"0", "1", "2", "3", "4"} <= set(boxes)
    for index, cell in enumerate(cells[:5]):
        cell_center = (cell.x0 + cell.x1) / 2
        index_center = (boxes[str(index)][0] + boxes[str(index)][2]) / 2
        assert abs(index_center - cell_center) < 0.25
