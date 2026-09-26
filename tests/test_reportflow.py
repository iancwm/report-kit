from geometry import node_rects, word_boxes

VERTICAL = r"""
\begin{diagram}[caption={A vertical flow.}]
  \begin{reportflow}[direction=vertical]
    \step{a}{Alpha}
    \step{b}{Bravo}
    \step{c}{Charlie}
    \flowedge{a}{b}
    \flowedge{b}{c}
  \end{reportflow}
\end{diagram}
"""

HORIZONTAL = VERTICAL.replace("[direction=vertical]", "")
LABELS = {"Alpha", "Bravo", "Charlie"}


def test_vertical_flow_stacks_steps_in_one_column(compile_doc):
    boxes = word_boxes(compile_doc(VERTICAL)[0], LABELS)
    assert set(boxes) == LABELS
    xs = [boxes[label][0] for label in ("Alpha", "Bravo", "Charlie")]
    ys = [boxes[label][1] for label in ("Alpha", "Bravo", "Charlie")]
    assert max(xs) - min(xs) < 5
    assert ys == sorted(ys)
    assert ys[1] - ys[0] > 20


def test_horizontal_flow_remains_the_default(compile_doc):
    boxes = word_boxes(compile_doc(HORIZONTAL)[0], LABELS)
    assert set(boxes) == LABELS
    xs = [boxes[label][0] for label in ("Alpha", "Bravo", "Charlie")]
    ys = [boxes[label][1] for label in ("Alpha", "Bravo", "Charlie")]
    assert max(ys) - min(ys) < 5
    assert xs == sorted(xs)


def test_vertical_flow_arrowheads_reach_target_nodes(compile_doc):
    page = compile_doc(VERTICAL)[0]
    nodes = sorted(node_rects(page, min_width=80), key=lambda rect: rect.y0)
    assert len(nodes) == 3

    for source, target in zip(nodes, nodes[1:]):
        connector_parts = [
            drawing["rect"]
            for drawing in page.get_drawings()
            if drawing["rect"].width < 8
            and drawing["rect"].height < 10
            and drawing["rect"].y0 >= source.y1 - 2
            and drawing["rect"].y1 <= target.y0 + 2
        ]
        assert connector_parts
        assert max(rect.y1 for rect in connector_parts) >= target.y0 - 0.1
