import pytest

from geometry import node_rects

FIGURE = r"""
\begin{diagram}[%scaption={A two-step flow.}]
  \begin{reportflow}[direction=vertical]
    \step{a}{Alpha}
    \step{b}{Bravo}
    \flowedge{a}{b}
  \end{reportflow}
\end{diagram}
"""


def widest(doc):
    rects = node_rects(doc[0], min_width=20)
    assert rects
    return max(rect.width for rect in rects)


def test_width_key_widens_the_figure(compile_doc):
    plain = widest(compile_doc(FIGURE % "", "plain"))
    wide = widest(compile_doc(FIGURE % r"width=\textwidth,", "wide"))
    assert wide > plain * 1.5


def test_scale_key_enlarges_the_figure(compile_doc):
    plain = widest(compile_doc(FIGURE % "", "plain"))
    scaled = widest(compile_doc(FIGURE % "scale=1.5,", "scaled"))
    assert scaled == pytest.approx(plain * 1.5, rel=0.05)


def test_omitting_size_keys_keeps_natural_geometry(compile_doc):
    assert 80 < widest(compile_doc(FIGURE % "", "plain")) < 100
