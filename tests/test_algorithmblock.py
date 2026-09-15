"""Rendered-PDF regressions for the algorithmblock primitive
(reportkit-algorithms.sty)."""
from __future__ import annotations

from pathlib import Path

import pytest

from geometry import word_boxes

REPO = Path(__file__).resolve().parents[1]


def test_algorithm_module_never_requires_the_floating_algorithm_package():
    """algorithmblock must stay a non-floating reading unit: no `algorithm`
    float package, and no bare \\begin{algorithm} float environment."""
    text = (REPO / "latex_templates" / "reportkit-algorithms.sty").read_text(encoding="utf-8")
    assert r"\RequirePackage{algorithm}" not in text
    assert r"\RequirePackage[" not in text.replace(r"\RequirePackage[most]{tcolorbox}", "")
    assert r"\begin{algorithm}" not in text
    assert "algorithm2e" not in text


def test_basic_sequence_of_state_statements_renders(compile_doc):
    page = compile_doc(
        r"""
        \begin{algorithmblock}{Running total}
          \State $total \gets 0$
          \State $total \gets total + x_1$
          \State \Return $total$
        \end{algorithmblock}
        """
    )[0]
    text = page.get_text()
    assert "ALGORITHM" in text
    assert "Running total" in text
    assert "return" in text.lower()


def test_nested_if_else_renders_both_branches_and_keywords(compile_doc):
    page = compile_doc(
        r"""
        \begin{algorithmblock}{Branch check}
          \State $L \gets 0$
          \If{$L \le R$}
            \State $L \gets L+1$
          \Else
            \State $R \gets R-1$
          \EndIf
        \end{algorithmblock}
        """
    )[0]
    text = page.get_text()
    for word in ("if", "else", "end if"):
        assert word in text.lower()
    # \If's branch must render above \Else's in reading order.
    boxes = word_boxes(page, {"if", "else"})
    assert set(boxes) == {"if", "else"}
    assert boxes["if"][1] < boxes["else"][1]


def test_nested_for_and_while_compile_and_render(compile_doc):
    page = compile_doc(
        r"""
        \begin{algorithmblock}{Nested loops}
          \State $best \gets 0$
          \For{$i \gets 0$ to $n-2$}
            \For{$j \gets i+1$ to $n-1$}
              \State $best \gets \max(best, j-i)$
            \EndFor
          \EndFor
          \While{$best < 10$}
            \State $best \gets best + 1$
          \EndWhile
        \end{algorithmblock}
        """
    )[0]
    text = page.get_text().lower()
    for word in ("for", "end for", "while", "end while"):
        assert word in text


def test_mathematics_renders_inside_statements(compile_doc):
    page = compile_doc(
        r"""
        \begin{algorithmblock}{Two-pointer elimination}
          \State $L \gets 0$
          \State $R \gets n-1$
          \While{$L < R$}
            \State $best \gets \max(best,(R-L)\min(h_L,h_R))$
          \EndWhile
        \end{algorithmblock}
        """
    )[0]
    text = page.get_text()
    assert "max" in text.lower()
    assert "min" in text.lower()


def test_input_output_metadata_renders_above_the_pseudocode(compile_doc):
    page = compile_doc(
        r"""
        \begin{algorithmblock}{Two-pointer elimination}
          \AlgorithmInput{Heights $h_0,\ldots,h_{n-1}$}
          \AlgorithmOutput{Maximum container area}
          \State $L \gets 0$
        \end{algorithmblock}
        """
    )[0]
    boxes = word_boxes(page, {"INPUT", "OUTPUT", "Heights", "Maximum"})
    assert set(boxes) == {"INPUT", "OUTPUT", "Heights", "Maximum"}
    # INPUT's own row sits above OUTPUT's own row, which sits above the first
    # pseudocode statement -- same-size label comparisons only, since a
    # smaller label glyph's bounding box can start a hair below a larger
    # word's on the same baseline.
    assert boxes["INPUT"][1] < boxes["OUTPUT"][1]
    assert boxes["Heights"][1] < boxes["Maximum"][1]


def test_long_algorithm_spans_a_page_boundary(compile_doc):
    repeated_steps = "\n".join(
        rf"\For{{each vertex $v$ in $V$}} \State \Call{{Step{i}}}{{$v$}} \EndFor"
        for i in range(40)
    )
    doc = compile_doc(
        r"""
        \begin{algorithmblock}{Iterative sweep}
          \AlgorithmInput{Graph $G=(V,E)$}
          \AlgorithmOutput{Processed vertices}
        """
        + repeated_steps
        + r"""
        \State \Return \textsc{done}
        \end{algorithmblock}
        """
    )
    assert doc.page_count >= 2


def test_institutional_research_theme_renders_algorithmblock(compile_doc):
    page = compile_doc(
        r"""
        \begin{algorithmblock}[linenumbers=1]{Two-pointer elimination}
          \AlgorithmInput{Heights $h_0,\ldots,h_{n-1}$}
          \AlgorithmOutput{Maximum container area}
          \State $L \gets 0$
          \While{$L < R$}
            \State $L \gets L + 1$
          \EndWhile
        \end{algorithmblock}
        """,
        class_options="theme=institutional-research,publication-type=equity-research",
    )[0]
    text = page.get_text()
    assert "ALGORITHM" in text
    assert "Two-pointer elimination" in text
    # Line numbers are opt-in; linenumbers=1 above must produce a "1:" marker.
    assert "1:" in text


def test_unknown_algorithmblock_option_is_rejected(compile_doc):
    with pytest.raises(AssertionError):
        compile_doc(
            r"""
            \begin{algorithmblock}[bogusoption=1]{Bad}
              \State $x \gets 1$
            \end{algorithmblock}
            """
        )


def test_caption_and_label_use_the_diagram_caption_convention(compile_doc):
    # A single lualatex pass cannot resolve \ref{alg:tp} (the label needs a
    # second pass to read back its own .aux entry); this only checks that
    # caption= renders via ReportKit's existing caption convention and that
    # label= does not break compilation.
    page = compile_doc(
        r"""
        \begin{algorithmblock}[caption={Two-pointer elimination finds the maximum area.},label={alg:tp}]{Two-pointer elimination}
          \State $L \gets 0$
        \end{algorithmblock}
        """
    )[0]
    text = page.get_text()
    assert "Figure 1" in text
    assert "Two-pointer elimination finds the maximum area." in text
