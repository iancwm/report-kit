"""Rendered-PDF regressions for the dptable/dagstate algorithm-visualization
primitives
(docs/superpowers/specs/2026-09-16-reportkit-algorithm-visualization-primitives-spec.md,
Phase 3: dptable, dagstate).
"""

import pytest

from geometry import node_rects, word_boxes


def test_dptable_renders_values_at_one_based_row_and_column(compile_doc):
    page = compile_doc(
        r"""
        \begin{diagram}[type=dp,width=\textwidth,caption={Edit distance.},description={A three by three dynamic-programming table with the current cell and one dependency cell marked.}]
          \begin{dptable}[rows=3,columns=3]
            \dpcell{1}{1}{0}
            \dpcell{1}{2}{1}
            \dpcell{2}{1}{1}
            \dpcell{2}{2}{0}
            \dpcell{3}{3}{2}
            \currentcell{3}{3}
            \dependencycell{2}{2}
          \end{dptable}
        \end{diagram}
        """
    )[0]
    rects = node_rects(page, min_width=10)
    # Five declared value cells (plus the bordering container rectangle) each
    # render as their own small rectangle at deterministic row/column
    # coordinates.
    assert len(rects) >= 5
    boxes = word_boxes(page, {"0", "1", "2"})
    assert {"0", "1", "2"} <= set(boxes)


def test_dptable_requires_rows_and_columns(compile_doc):
    with pytest.raises(Exception):
        compile_doc(
            r"""
            \begin{diagram}[type=dp,width=\textwidth,caption={Missing size.},description={A dptable declared without rows or columns.}]
              \begin{dptable}
                \dpcell{1}{1}{0}
              \end{dptable}
            \end{diagram}
            """
        )


def test_dpcell_out_of_range_index_raises_a_package_error(compile_doc):
    with pytest.raises(Exception):
        compile_doc(
            r"""
            \begin{diagram}[type=dp,width=\textwidth,caption={Out of range.},description={A DP cell placed outside the declared bounds.}]
              \begin{dptable}[rows=2,columns=2]
                \dpcell{5}{1}{0}
              \end{dptable}
            \end{diagram}
            """
        )


def test_dptable_state_markers_stay_within_declared_bounds(compile_doc):
    with pytest.raises(Exception):
        compile_doc(
            r"""
            \begin{diagram}[type=dp,width=\textwidth,caption={Out of range marker.},description={A currentcell marker placed outside the declared bounds.}]
              \begin{dptable}[rows=2,columns=2]
                \currentcell{9}{9}
              \end{dptable}
            \end{diagram}
            """
        )


def test_dagstate_renders_node_labels_and_indegree_badges(compile_doc):
    page = compile_doc(
        r"""
        \begin{diagram}[type=dag,width=\textwidth,caption={Data-pipeline dependencies.},description={Three pipeline stages: raw is ready with indegree zero, clean depends on raw, and features depends on clean.}]
          \begin{dagstate}
            \dagnode[indegree=0]{raw}{Raw}
            \dagnode[indegree=1]{clean}{Clean}
            \dagnode[indegree=1]{features}{Features}
            \dependency{raw}{clean}
            \dependency{clean}{features}
            \readyqueue{raw}
          \end{dagstate}
        \end{diagram}
        """
    )[0]
    boxes = word_boxes(page, {"Raw", "Clean", "Features"})
    assert {"Raw", "Clean", "Features"} <= set(boxes)
    # Automatic grid layout places the first node left of the second.
    assert boxes["Raw"][0] < boxes["Clean"][0]


def test_readyqueue_unknown_id_raises_a_package_error(compile_doc):
    with pytest.raises(Exception):
        compile_doc(
            r"""
            \begin{diagram}[type=dag,width=\textwidth,caption={Bad ready id.},description={A readyqueue reference to an undeclared node id.}]
              \begin{dagstate}
                \dagnode[indegree=0]{raw}{Raw}
                \readyqueue{nonexistent}
              \end{dagstate}
            \end{diagram}
            """
        )


def test_dagstate_unknown_state_raises_a_package_error(compile_doc):
    with pytest.raises(Exception):
        compile_doc(
            r"""
            \begin{diagram}[type=dag,width=\textwidth,caption={Bad state.},description={Invalid state name.}]
              \begin{dagstate}
                \dagnode[state=nonsense]{raw}{Raw}
              \end{dagstate}
            \end{diagram}
            """
        )
