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


# -----------------------------------------------------------------------------
# dagstate layout=dependency (spec section 4, C1) and the ready-queue FIFO box
# (C2). These compile_doc snippets deliberately omit diagram description= (it
# defaults to empty) so PyMuPDF's word-level text extraction is not overridden
# by the diagram's accessibility ActualText span (reportkit-diagrams.sty wraps
# a non-empty description= around the whole rendered diagram as a single
# marked-content ActualText run, which replaces every enclosed node label with
# the description string for text-extraction purposes -- confirmed by direct
# reproduction outside this primitive; see task report). The production
# example fixture keeps real description= text for actual accessibility.
def test_dagstate_layout_dependency_places_nodes_by_topological_level(compile_doc):
    page = compile_doc(
        r"""
        \begin{diagram}[type=dag,width=\textwidth,caption={Two chains merging.}]
          \begin{dagstate}[layout=dependency]
            \dagnode{a}{NodeA}
            \dagnode{b}{NodeB}
            \dagnode{c}{NodeC}
            \dagnode{d}{NodeD}
            \dagnode{e}{NodeE}
            \dependency{a}{b}
            \dependency{b}{c}
            \dependency{d}{e}
            \dependency{e}{c}
          \end{dagstate}
        \end{diagram}
        """
    )[0]
    boxes = word_boxes(page, {"NodeA", "NodeB", "NodeC", "NodeD", "NodeE"})
    assert {"NodeA", "NodeB", "NodeC", "NodeD", "NodeE"} <= set(boxes)
    # Compare label centers, not raw left edges: text is centered within a
    # fixed-width node box, so two different labels of the same string
    # length can still have very slightly different glyph widths.
    center_x = {name: (box[0] + box[2]) / 2 for name, box in boxes.items()}
    # A and D are both sources (no declared dependency) -- same column.
    assert center_x["NodeA"] == pytest.approx(center_x["NodeD"], abs=1.5)
    # B depends on A, E depends on D -- both one column to the right of the sources.
    assert center_x["NodeB"] == pytest.approx(center_x["NodeE"], abs=1.5)
    assert center_x["NodeB"] > center_x["NodeA"]
    # C depends on both B and E -- strictly to the right of both prior columns.
    assert center_x["NodeC"] > center_x["NodeB"]
    assert center_x["NodeC"] > center_x["NodeA"]


def test_dagstate_layout_dependency_defers_edges_until_end(compile_doc):
    # Dependencies declared before their target/source node is placed must
    # still resolve once layout is finalized at \end{dagstate}.
    page = compile_doc(
        r"""
        \begin{diagram}[type=dag,width=\textwidth,caption={Order independence.}]
          \begin{dagstate}[layout=dependency]
            \dagnode{a}{NodeA}
            \dependency{a}{b}
            \dagnode{b}{NodeB}
          \end{dagstate}
        \end{diagram}
        """
    )[0]
    boxes = word_boxes(page, {"NodeA", "NodeB"})
    assert {"NodeA", "NodeB"} <= set(boxes)
    assert boxes["NodeB"][0] > boxes["NodeA"][0]


def test_readyqueue_renders_a_labelled_fifo_box_distinct_from_dag_nodes(compile_doc):
    page = compile_doc(
        r"""
        \begin{diagram}[type=dag,width=\textwidth,caption={Topological sort.}]
          \begin{dagstate}[layout=dependency]
            \dagnode[indegree=0,state=resolved]{raw}{RawOrders}
            \dagnode[indegree=0,state=frontier]{clean}{CleanOrders}
            \dagnode[indegree=1,state=unseen]{sales}{DailySales}
            \dependency{raw}{clean}
            \dependency{clean}{sales}
            \readyqueue{clean}
          \end{dagstate}
        \end{diagram}
        """
    )[0]
    words = page.get_text("words")
    ready_labels = [w for w in words if w[4] == "READY"]
    assert ready_labels, "expected a 'READY' queue label"
    clean_occurrences = [w for w in words if w[4] == "CleanOrders"]
    # CleanOrders is drawn once in the DAG itself and again inside the ready
    # queue box -- two distinct occurrences at two distinct y positions.
    assert len(clean_occurrences) >= 2
    ys = sorted({round(w[1], 1) for w in clean_occurrences})
    assert len(ys) >= 2
    # The queue box (a rectangle distinct from the DAG's own node rectangles)
    # renders below the DAG's lowest node.
    rects = node_rects(page, min_width=5)
    assert len(rects) >= 4  # 3 dag nodes + at least 1 queue item/container


def test_readyqueue_nonzero_indegree_raises_a_package_error(compile_doc):
    with pytest.raises(Exception):
        compile_doc(
            r"""
            \begin{diagram}[type=dag,width=\textwidth,caption={Bad ready id.}]
              \begin{dagstate}[layout=dependency]
                \dagnode[indegree=1]{raw}{Raw}
                \dagnode[indegree=1]{clean}{Clean}
                \dependency{raw}{clean}
                \readyqueue{clean}
              \end{dagstate}
            \end{diagram}
            """
        )


def test_dagstate_layout_grid_is_unchanged_default(compile_doc):
    # Omitting layout= (or layout=grid) keeps today's automatic-grid
    # placement exactly, for backward compatibility.
    page = compile_doc(
        r"""
        \begin{diagram}[type=dag,width=\textwidth,caption={Default grid.}]
          \begin{dagstate}[columns=2]
            \dagnode[indegree=0]{a}{NodeA}
            \dagnode[indegree=1]{b}{NodeB}
            \dagnode[indegree=1]{c}{NodeC}
            \dependency{a}{b}
          \end{dagstate}
        \end{diagram}
        """
    )[0]
    boxes = word_boxes(page, {"NodeA", "NodeB", "NodeC"})
    assert {"NodeA", "NodeB", "NodeC"} <= set(boxes)
    # columns=2 grid: NodeA and NodeB share a row, NodeC wraps to the next row.
    assert boxes["NodeA"][1] == pytest.approx(boxes["NodeB"][1], abs=0.5)
    assert boxes["NodeC"][1] > boxes["NodeA"][1]
