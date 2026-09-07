from geometry import word_boxes

COMPARISON = r"""
\begin{diagram}[width=\textwidth,caption={Join cardinality.}]
  \begin{reportcompare}
    \panel{before}{Before join}
    \panelitem{before}{0}{one order row}
    \panelitem{before}{1}{grain: order}
    \panel{after}{After join}
    \panelitem{after}{0}{three item rows}
    \panelitem{after}{1}{grain: order item}
    \transformarrow{join multiplies rows}
  \end{reportcompare}
\end{diagram}
"""


def test_panels_and_transform_render(compile_doc):
    page = compile_doc(COMPARISON)[0]
    boxes = word_boxes(page, {"Before", "After", "one", "multiplies"})
    assert boxes["After"][0] > boxes["Before"][2]
    assert boxes["one"][1] > boxes["Before"][1]
    assert "multiplies" in page.get_text()
