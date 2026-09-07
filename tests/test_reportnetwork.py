from geometry import node_rects, word_boxes

CHAIN = r"""
\begin{diagram}[caption={A four-stage chain.}]
  \begin{reportnetwork}
    \networknode{n1}{Source}
    \networknode{n2}{Ingest}
    \networknode{n3}{Store}
    \networknode{n4}{Serve}
    \networkedge[flow]{n1}{n2}
    \networkedge[flow]{n2}{n3}
    \networkedge[flow]{n3}{n4}
  \end{reportnetwork}
\end{diagram}
"""


def test_adjacent_grid_nodes_have_clearance(compile_doc):
    rects = node_rects(compile_doc(CHAIN)[0], min_width=84)
    assert len(rects) >= 4
    row = sorted(rects[:4], key=lambda rect: rect.x0)
    assert all(row[index + 1].x0 - row[index].x1 >= 2 for index in range(3))


def test_grid_wraps_after_four_nodes(compile_doc):
    body = CHAIN.replace(
        r"\networkedge[flow]{n3}{n4}",
        "\\networkedge[flow]{n3}{n4}\n    \\networknode{n5}{Monitor}",
    )
    boxes = word_boxes(compile_doc(body)[0], {"Source", "Monitor"})
    assert boxes["Monitor"][1] > boxes["Source"][1] + 20
    assert abs(boxes["Monitor"][0] - boxes["Source"][0]) < 5
