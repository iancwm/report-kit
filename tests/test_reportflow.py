from geometry import word_boxes

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
