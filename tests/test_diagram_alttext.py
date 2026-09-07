from geometry import stream_contains

ALT = "ZZUNIQUEALTTEXT a two-step flow from Alpha to Bravo"
WITH_DESCRIPTION = rf"""
\begin{{diagram}}[caption={{A caption.}},source={{A source.}},description={{{ALT}}}]
  \begin{{reportflow}}
    \step{{a}}{{Alpha}}
    \step{{b}}{{Bravo}}
    \flowedge{{a}}{{b}}
  \end{{reportflow}}
\end{{diagram}}
"""


def test_description_is_embedded_in_the_pdf(compile_doc):
    assert stream_contains(compile_doc(WITH_DESCRIPTION), ALT.encode("latin-1"))


def test_caption_and_source_still_render(compile_doc):
    text = compile_doc(WITH_DESCRIPTION)[0].get_text()
    assert "A caption" in text and "A source" in text
