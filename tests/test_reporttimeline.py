from geometry import word_boxes

TIMELINE = r"""
\begin{diagram}[width=\textwidth,caption={Event time versus processing time.}]
  \begin{reporttimeline}[tracks={Event time,Processing time}]
    \event{Event time}{0.15}{A}
    \event{Event time}{0.35}{B}
    \event{Processing time}{0.45}{A}
    \event{Processing time}{0.80}{B}
    \skewarrow{Event time}{0.15}{Processing time}{0.45}
    \watermark{Processing time}{0.65}{watermark}
  \end{reporttimeline}
\end{diagram}
"""


def test_tracks_and_watermark_render(compile_doc):
    page = compile_doc(TIMELINE)[0]
    boxes = word_boxes(page, {"Event", "Processing", "watermark"})
    assert set(boxes) == {"Event", "Processing", "watermark"}
    assert boxes["Processing"][1] > boxes["Event"][1] + 15
    assert "watermark" in page.get_text()
