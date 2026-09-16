"""Rendered-PDF regressions for the Phase 1 algorithm-state visualization
primitives (reportkit-algorithm-viz.sty): the shared state vocabulary,
`arraystate`, and `algorithmtrace`."""
from __future__ import annotations

from pathlib import Path

import pytest

from geometry import word_boxes

REPO = Path(__file__).resolve().parents[1]


def test_module_never_opens_its_own_tikzpicture():
    """arraystate/algorithmtrace must draw into the diagram wrapper's own
    tikzpicture, like reportarchitecture or reportcycle, rather than opening
    a second one of their own."""
    text = (REPO / "latex_templates" / "reportkit-algorithm-viz.sty").read_text(encoding="utf-8")
    assert r"\begin{tikzpicture}" not in text


def test_two_pointer_array_renders_values_pointers_and_indices(compile_doc):
    page = compile_doc(
        r"""
        \begin{diagram}[caption={Two-pointer scan.}]
        \begin{arraystate}[indices=true]
          \cell{-4}
          \cell{-1}
          \cell{-1}
          \cell{0}
          \cell{1}
          \cell{2}
          \pointer[below]{L}{2}
          \pointer[below]{R}{5}
          \range[state=active]{2}{5}
        \end{arraystate}
        \end{diagram}
        """
    )[0]
    text = page.get_text()
    assert "-4" in text
    boxes = word_boxes(page, {"L", "R"})
    assert set(boxes) == {"L", "R"}
    # L marks index 2, R marks index 5, so L's box sits left of R's.
    assert boxes["L"][0] < boxes["R"][0]


def test_all_nine_states_compile_without_error(compile_doc):
    page = compile_doc(
        r"""
        \begin{diagram}[caption={Nine states.}]
        \begin{arraystate}
          \cell[state=current]{Cu}
          \cell[state=active]{Ac}
          \cell[state=candidate]{Ca}
          \cell[state=frontier]{Fr}
          \cell[state=visited]{Vi}
          \cell[state=resolved]{Re}
          \cell[state=discarded]{Di}
          \cell[state=blocked]{Bl}
          \cell[state=unseen]{Un}
        \end{arraystate}
        \end{diagram}
        """
    )[0]
    text = page.get_text()
    for label in ("Cu", "Ac", "Ca", "Fr", "Vi", "Re", "Di", "Bl", "Un"):
        assert label in text


def test_annotation_renders_below_the_array(compile_doc):
    page = compile_doc(
        r"""
        \begin{diagram}[caption={Annotated array.}]
        \begin{arraystate}
          \cell{1}
          \cell{2}
          \cell{3}
          \annotation{Sum is six}
        \end{arraystate}
        \end{diagram}
        """
    )[0]
    assert "Sum is six" in page.get_text()


def test_multi_row_prefix_sum_renders_both_rows_and_labels(compile_doc):
    page = compile_doc(
        r"""
        \begin{diagram}[caption={Prefix sums.}]
        \begin{arraystate}[rows=2]
          \row{values}{3,1,4,2}
          \row{prefix}{0,3,4,8,10}
          \range[row=values,state=active]{1}{3}
        \end{arraystate}
        \end{diagram}
        """
    )[0]
    text = page.get_text()
    assert "values" in text
    assert "prefix" in text
    for value in ("3", "1", "4", "2", "0", "8", "10"):
        assert value in text
    boxes = word_boxes(page, {"values", "prefix"})
    assert set(boxes) == {"values", "prefix"}
    # "values" is declared as the first row, so it sits above "prefix".
    assert boxes["values"][1] < boxes["prefix"][1]


def test_algorithmtrace_renders_snapshots_in_reading_order(compile_doc):
    page = compile_doc(
        r"""
        \begin{diagram}[caption={Sliding window advances by one.}]
        \begin{algorithmtrace}[columns=3]
          \snapshot{Initial}{\begin{arraystate}\cell{4}\cell{2}\cell{7}\cell{1}\range[state=active]{0}{1}\end{arraystate}}
          \snapshot{Advance right}{\begin{arraystate}\cell{4}\cell{2}\cell{7}\cell{1}\range[state=active]{1}{2}\end{arraystate}}
          \snapshot{Advance again}{\begin{arraystate}\cell{4}\cell{2}\cell{7}\cell{1}\range[state=active]{2}{3}\end{arraystate}}
        \end{algorithmtrace}
        \end{diagram}
        """
    )[0]
    boxes = word_boxes(page, {"Initial", "Advance"})
    assert set(boxes) == {"Initial", "Advance"}
    assert boxes["Initial"][0] < boxes["Advance"][0]


def test_unknown_state_is_rejected(compile_doc):
    with pytest.raises(AssertionError):
        compile_doc(
            r"""
            \begin{diagram}[caption={x},description={x}]
            \begin{arraystate}
              \cell[state=bogus]{1}
            \end{arraystate}
            \end{diagram}
            """
        )


def test_pointer_index_out_of_range_is_rejected(compile_doc):
    with pytest.raises(AssertionError):
        compile_doc(
            r"""
            \begin{diagram}[caption={x},description={x}]
            \begin{arraystate}
              \cell{1}
              \cell{2}
              \pointer[below]{L}{5}
            \end{arraystate}
            \end{diagram}
            """
        )


def test_cell_is_rejected_when_rows_is_two_or_more(compile_doc):
    with pytest.raises(AssertionError):
        compile_doc(
            r"""
            \begin{diagram}[caption={x},description={x}]
            \begin{arraystate}[rows=2]
              \cell{1}
            \end{arraystate}
            \end{diagram}
            """
        )


def test_range_without_row_key_is_rejected_in_multi_row_mode(compile_doc):
    with pytest.raises(AssertionError):
        compile_doc(
            r"""
            \begin{diagram}[caption={x},description={x}]
            \begin{arraystate}[rows=2]
              \row{a}{1,2}
              \row{b}{3,4}
              \range[state=active]{0}{1}
            \end{arraystate}
            \end{diagram}
            """
        )


def test_arraystate_requires_at_least_one_cell(compile_doc):
    with pytest.raises(AssertionError):
        compile_doc(
            r"""
            \begin{diagram}[caption={x},description={x}]
            \begin{arraystate}
            \end{arraystate}
            \end{diagram}
            """
        )


def test_algorithmtrace_requires_at_least_one_snapshot(compile_doc):
    with pytest.raises(AssertionError):
        compile_doc(
            r"""
            \begin{diagram}[caption={x},description={x}]
            \begin{algorithmtrace}
            \end{algorithmtrace}
            \end{diagram}
            """
        )


def test_caption_and_label_use_the_diagram_caption_convention(compile_doc):
    page = compile_doc(
        r"""
        \begin{diagram}[caption={Two-pointer elimination finds the maximum area.},label={fig:tp},description={A sorted array with pointers.}]
        \begin{arraystate}
          \cell{1}
          \cell{2}
        \end{arraystate}
        \end{diagram}
        """
    )[0]
    text = page.get_text()
    assert "Figure 1" in text
    assert "Two-pointer elimination finds the maximum area." in text


def test_institutional_research_theme_renders_arraystate(compile_doc):
    page = compile_doc(
        r"""
        \begin{diagram}[caption={Two-pointer scan.}]
        \begin{arraystate}
          \cell[state=active]{1}
          \cell[state=current]{2}
          \pointer[below]{L}{0}
        \end{arraystate}
        \end{diagram}
        """,
        class_options="theme=institutional-research,publication-type=equity-research",
    )[0]
    text = page.get_text()
    assert "L" in text
