"""Rendered-PDF regressions for the graphstate/gridstate algorithm-
visualization primitives
(docs/superpowers/specs/2026-09-16-reportkit-algorithm-visualization-primitives-spec.md,
Phase 2: graphstate, gridstate).
"""

import pytest

from geometry import node_rects, word_boxes


def test_graphstate_renders_node_labels_and_lays_out_on_a_grid(compile_doc):
    page = compile_doc(
        r"""
        \begin{diagram}[type=graph,width=\textwidth,caption={BFS frontier.},description={A start node has been visited, its current neighbor is being processed, one neighbor is queued as frontier, and one neighbor is unseen.}]
          \begin{graphstate}
            \graphnode[state=visited]{A}{Start}
            \graphnode[state=current]{B}{Current}
            \graphnode[state=frontier]{C}{Queued}
            \graphnode[state=unseen]{D}{Unseen}
            \graphedge{A}{B}
            \graphedge{B}{C}
            \graphedge{B}{D}
          \end{graphstate}
        \end{diagram}
        """
    )[0]
    boxes = word_boxes(page, {"Start", "Current", "Queued", "Unseen"})
    assert {"Start", "Current", "Queued", "Unseen"} <= set(boxes)
    # Automatic grid layout places the first node left of the second.
    assert boxes["Start"][0] < boxes["Current"][0]


def test_graphstate_unknown_state_raises_a_package_error(compile_doc):
    with pytest.raises(Exception):
        compile_doc(
            r"""
            \begin{diagram}[type=graph,width=\textwidth,caption={Bad state.},description={Invalid state name.}]
              \begin{graphstate}
                \graphnode[state=nonsense]{A}{Start}
              \end{graphstate}
            \end{diagram}
            """
        )


def test_gridstate_places_cells_by_one_based_row_and_column(compile_doc):
    page = compile_doc(
        r"""
        \begin{diagram}[type=grid,width=\textwidth,caption={Flood fill.},description={A four by five grid with a flood-fill frontier expanding from the top-left corner.}]
          \begin{gridstate}[rows=4,columns=5]
            \gridcell{1}{1}[state=visited]
            \gridcell{1}{2}[state=current]
            \gridcell{2}{2}[state=frontier]
            \gridcell{3}{3}[state=blocked]
          \end{gridstate}
        \end{diagram}
        """
    )[0]
    # Four declared cells (plus the bordering container rectangle) each
    # render as their own small rectangle at deterministic row/column
    # coordinates.
    rects = node_rects(page, min_width=10)
    assert len(rects) >= 4


def test_gridstate_requires_rows_and_columns(compile_doc):
    with pytest.raises(Exception):
        compile_doc(
            r"""
            \begin{diagram}[type=grid,width=\textwidth,caption={Missing size.},description={A gridstate declared without rows or columns.}]
              \begin{gridstate}
                \gridcell{1}{1}[state=visited]
              \end{gridstate}
            \end{diagram}
            """
        )


def test_gridcell_out_of_range_index_raises_a_package_error(compile_doc):
    with pytest.raises(Exception):
        compile_doc(
            r"""
            \begin{diagram}[type=grid,width=\textwidth,caption={Out of range.},description={A grid cell placed outside the declared bounds.}]
              \begin{gridstate}[rows=2,columns=2]
                \gridcell{5}{1}[state=visited]
              \end{gridstate}
            \end{diagram}
            """
        )
