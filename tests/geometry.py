"""PyMuPDF helpers for rendered ReportKit geometry assertions."""


def word_boxes(page, labels):
    found = {}
    for x0, y0, x1, y1, text, *_ in page.get_text("words"):
        if text in labels and text not in found:
            found[text] = (x0, y0, x1, y1)
    return found


def node_rects(page, min_width=40.0):
    rects = [drawing["rect"] for drawing in page.get_drawings() if drawing["rect"].width >= min_width and 15.0 <= drawing["rect"].height <= 200.0]
    return sorted(rects, key=lambda rect: (rect.y0, rect.x0))


def stream_contains(doc, needle: bytes) -> bool:
    for xref in range(1, doc.xref_length()):
        try:
            stream = doc.xref_stream(xref)
        except Exception:
            continue
        if stream and needle in stream:
            return True
    return False
