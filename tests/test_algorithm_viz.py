"""Rendered-PDF regressions for the algorithm-visualization primitives
(docs/superpowers/specs/2026-09-16-reportkit-algorithm-visualization-primitives-spec.md,
Phase 1: shared state vocabulary, arraystate, windowstate, algorithmtrace).
"""

import pytest

from geometry import word_boxes


def test_arraystate_renders_values_indices_and_pointer_labels(compile_doc):
    page = compile_doc(
        r"""
        \begin{diagram}[type=array,width=\textwidth,caption={Two-pointer scan.},description={A sorted array with left and right pointers bounding the active range.}]
          \begin{arraystate}
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
    boxes = word_boxes(page, {"-4", "-1", "0", "1", "2", "L", "R"})
    assert {"-4", "0", "1", "2", "L", "R"} <= set(boxes)
    # Pointer labels sit below the cell row they annotate.
    cell_top = min(box[1] for name, box in boxes.items() if name in {"-4", "0", "1", "2"})
    assert boxes["L"][1] > cell_top
    assert boxes["R"][1] > cell_top
    assert boxes["L"][0] < boxes["R"][0]


def test_arraystate_multi_row_declares_named_aligned_rows(compile_doc):
    page = compile_doc(
        r"""
        \begin{diagram}[type=array,width=\textwidth,caption={Prefix sums.},description={A four-element array aligned with its five-element prefix-sum row.}]
          \begin{arraystate}
            \row{values}{3,1,4,2}
            \row{prefix}{0,3,4,8,10}
            \range[row=values,state=active]{1}{2}
            \annotation{$P_4 - P_1 = 7$}
          \end{arraystate}
        \end{diagram}
        """
    )[0]
    boxes = word_boxes(page, {"values", "prefix", "3", "4", "8", "10"})
    assert {"values", "prefix", "8", "10"} <= set(boxes)
    # The prefix row renders below the values row.
    assert boxes["prefix"][1] > boxes["values"][1]


def test_windowstate_marks_active_window_and_entering_leaving(compile_doc):
    page = compile_doc(
        r"""
        \begin{diagram}[type=array,width=\textwidth,caption={Sliding window.},description={A six-element array with a window from index two to four and entering/leaving markers.}]
          \begin{windowstate}
            \values{4,2,7,1,3,6}
            \window{2}{4}
            \entering{5}
            \leaving{1}
          \end{windowstate}
        \end{diagram}
        """
    )[0]
    text = page.get_text()
    assert "entering" in text
    assert "leaving" in text
    boxes = word_boxes(page, {"4", "2", "7", "1", "3", "6", "L", "R"})
    assert {"L", "R"} <= set(boxes)


def test_algorithmtrace_orders_snapshots_left_to_right(compile_doc):
    page = compile_doc(
        r"""
        \begin{diagram}[type=trace,width=\textwidth,caption={Window advance.},description={Two ordered snapshots show the window advancing by one element.}]
          \begin{algorithmtrace}[columns=2]
            \snapshot{Initial}{\begin{arraystate}[indices=false]\cell{4}\cell{2}\cell{7}\end{arraystate}}
            \snapshot{Advance}{\begin{arraystate}[indices=false]\cell{2}\cell{7}\cell{1}\end{arraystate}}
          \end{algorithmtrace}
        \end{diagram}
        """
    )[0]
    boxes = word_boxes(page, {"Initial", "Advance"})
    assert {"Initial", "Advance"} <= set(boxes)
    assert boxes["Initial"][0] < boxes["Advance"][0]


def test_unknown_algorithm_state_raises_a_package_error(compile_doc):
    with pytest.raises(Exception):
        compile_doc(
            r"""
            \begin{diagram}[type=array,width=\textwidth,caption={Bad state.},description={Invalid state name.}]
              \begin{arraystate}
                \cell[state=nonsense]{1}
              \end{arraystate}
            \end{diagram}
            """
        )
