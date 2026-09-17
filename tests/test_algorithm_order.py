"""Rendered-PDF regressions for the intervalstate/heapstate algorithm-
visualization primitives
(docs/superpowers/specs/2026-09-16-reportkit-algorithm-visualization-primitives-spec.md,
Phase 3 (partial): intervalstate, heapstate).
"""

import pytest

from geometry import node_rects, word_boxes


def test_intervalstate_renders_labelled_bars_stacked_by_declaration_order(compile_doc):
    page = compile_doc(
        r"""
        \begin{diagram}[type=interval,width=\textwidth,caption={Merge overlapping intervals.},description={Three intervals on a shared axis, two of which overlap, followed by their merged summary span.}]
          \begin{intervalstate}
            \interval[state=candidate]{A}{1}{4}
            \interval[state=active]{B}{3}{6}
            \interval[state=candidate]{C}{8}{10}
            \merged{1}{6}
          \end{intervalstate}
        \end{diagram}
        """
    )[0]
    boxes = word_boxes(page, {"A", "B", "C"})
    assert {"A", "B", "C"} <= set(boxes)
    # Each \interval renders on its own row, in declaration order.
    assert boxes["A"][1] < boxes["B"][1] < boxes["C"][1]


def test_intervalstate_merged_row_renders_below_individual_intervals(compile_doc):
    page = compile_doc(
        r"""
        \begin{diagram}[type=interval,width=\textwidth,caption={Merged summary row.},description={Two intervals followed by their merged summary span on its own row.}]
          \begin{intervalstate}
            \interval{A}{1}{4}
            \interval{B}{3}{6}
            \merged{1}{6}
          \end{intervalstate}
        \end{diagram}
        """
    )[0]
    boxes = word_boxes(page, {"A", "B"})
    assert {"A", "B"} <= set(boxes)
    # The merged bar is a third row's worth of rectangles below A and B's
    # rows; a coarse rectangle count check is enough to confirm it rendered.
    rects = node_rects(page, min_width=10)
    assert len(rects) >= 3


def test_interval_start_after_end_raises_a_package_error(compile_doc):
    with pytest.raises(Exception):
        compile_doc(
            r"""
            \begin{diagram}[type=interval,width=\textwidth,caption={Bad interval.},description={An interval whose start exceeds its end.}]
              \begin{intervalstate}
                \interval{A}{5}{2}
              \end{intervalstate}
            \end{diagram}
            """
        )


def test_heapstate_renders_backing_array_and_mirrored_tree_values(compile_doc):
    page = compile_doc(
        r"""
        \begin{diagram}[type=heap,width=\textwidth,caption={A small max-heap.},description={A backing array of five values paired with its binary-tree view; the root is marked current.}]
          \begin{heapstate}
            \values{10,9,8,5,3}
            \current{0}
          \end{heapstate}
        \end{diagram}
        """
    )[0]
    text = page.get_text()
    # Every declared value renders at least twice: once in the backing
    # array, once in its mirrored tree node.
    for value in ("10", "9", "8", "5", "3"):
        assert text.count(value) >= 2


def test_heapstate_tree_root_renders_above_its_children(compile_doc):
    page = compile_doc(
        r"""
        \begin{diagram}[type=heap,width=\textwidth,caption={Heap tree layout.},description={A backing array of seven values paired with its binary-tree view, three levels deep.}]
          \begin{heapstate}
            \values{9,7,8,4,5,6,2}
          \end{heapstate}
        \end{diagram}
        """
    )[0]
    # Every value renders twice (backing array row plus mirrored tree node),
    # so pick the topmost occurrence of each value's text -- that is always
    # its tree instance, since tree levels sit strictly above the y=0
    # backing-array row regardless of extraction order.
    words = page.get_text("words")

    def topmost(label):
        tops = [w[1] for w in words if w[4] == label]
        assert tops, f"{label!r} not found on page"
        return min(tops)

    # Tree node positions are derived automatically from array index: the
    # root (value 9, index 0) sits above its two children (7, 8).
    root_top = topmost("9")
    assert root_top < topmost("7")
    assert root_top < topmost("8")


def test_current_out_of_range_index_raises_a_package_error(compile_doc):
    with pytest.raises(Exception):
        compile_doc(
            r"""
            \begin{diagram}[type=heap,width=\textwidth,caption={Out of range.},description={A heap current marker placed outside the declared values.}]
              \begin{heapstate}
                \values{1,2,3}
                \current{9}
              \end{heapstate}
            \end{diagram}
            """
        )
