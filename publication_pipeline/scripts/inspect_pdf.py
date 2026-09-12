#!/usr/bin/env python3
"""Run deterministic PDF checks using PyMuPDF only."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

try:
    from _bootstrap import ensure_reportkit_importable
except ImportError:  # imported as publication_pipeline.scripts.inspect_pdf
    from ._bootstrap import ensure_reportkit_importable

ensure_reportkit_importable()

try:
    import pymupdf as fitz
except ImportError:  # PyMuPDF < 1.26
    try:
        import fitz  # type: ignore
    except ImportError:
        fitz = None  # type: ignore[assignment]

from reportkit.diagnostics import diagnostic_envelope, make_diagnostic  # noqa: E402


def inspect(path: Path) -> dict:
    if fitz is None:
        raise ModuleNotFoundError("PyMuPDF is not installed")
    doc = fitz.open(path)
    outside: list[dict[str, object]] = []
    near_margin: list[dict[str, object]] = []
    blank_pages: list[int] = []
    dimensions: list[dict[str, object]] = []
    fonts: dict[str, dict[str, object]] = {}
    margin = 4.0
    for page_number, page in enumerate(doc, 1):
        media = page.rect
        dimensions.append({"page": page_number, "width": round(media.width, 3), "height": round(media.height, 3)})
        words = page.get_text("words")
        images = page.get_images(full=True)
        drawings = page.get_drawings()
        if not words and not images and not drawings:
            blank_pages.append(page_number)
        for font in page.get_fonts(full=True):
            font_key = str(font[3] or font[4] or font[0])
            fonts.setdefault(font_key, {"name": font_key, "pages": []})["pages"].append(page_number)
        for word in words:
            x0, y0, x1, y1, text = word[:5]
            if x0 < media.x0 - 0.5 or y0 < media.y0 - 0.5 or x1 > media.x1 + 0.5 or y1 > media.y1 + 0.5:
                outside.append({"page": page_number, "text": text, "bbox": [x0, y0, x1, y1], "media_box": [media.x0, media.y0, media.x1, media.y1]})
            elif x0 < media.x0 + margin or y0 < media.y0 + margin or x1 > media.x1 - margin or y1 > media.y1 - margin:
                near_margin.append({"page": page_number, "text": text, "bbox": [x0, y0, x1, y1], "margin_pt": margin})
    toc = doc.get_toc(simple=True)
    diagnostics = [make_diagnostic(
        "pdf_geometry", f"content {item['text']!r} lies outside the page media box",
        code="RK_PDF_OUTSIDE_MEDIA_BOX", source={"file": str(path)},
        details={"page": item["page"], "bbox": item["bbox"], "media_box": item["media_box"]},
    ) for item in outside]
    diagnostics.extend(make_diagnostic(
        "blank_page", f"page {page} is blank", code="RK_PDF_BLANK_PAGE",
        source={"file": str(path)}, details={"page": page},
    ) for page in blank_pages)
    return diagnostic_envelope(
        diagnostics,
        passed=not outside and not blank_pages and len(doc) > 0,
        page_count=len(doc),
        outside_media_box=outside,
        near_margin_content=near_margin,
        blank_pages=blank_pages,
        page_dimensions=dimensions,
        bookmarks={"count": len(toc), "items": toc},
        fonts=sorted(fonts.values(), key=lambda item: str(item["name"])),
        metadata=doc.metadata,
        link_count=sum(len(page.get_links()) for page in doc),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--json", dest="json_path", type=Path)
    args = parser.parse_args()
    try:
        result = inspect(args.pdf)
    except ModuleNotFoundError as exc:
        result = diagnostic_envelope([
            make_diagnostic("environment_error", f"PDF inspection requires PyMuPDF: {exc}", code="RK_PYMUPDF_MISSING")
        ], passed=False)
        if args.json_path:
            args.json_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"FAIL: PDF inspection requires PyMuPDF: {exc}", file=sys.stderr)
        return 5
    except Exception as exc:
        result = diagnostic_envelope([
            make_diagnostic("pdf_geometry", f"PDF inspection failed: {exc}", code="RK_PDF_INSPECTION")
        ], passed=False)
        if args.json_path:
            args.json_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"FAIL: PDF inspection failed: {exc}", file=sys.stderr)
        return 3
    if args.json_path:
        args.json_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not result["passed"]:
        print(f"FAIL: {len(result['outside_media_box'])} glyph boxes fall outside the media box; {len(result['blank_pages'])} blank pages", file=sys.stderr)
        return 3
    print(f"PASS: PDF inspection ({result['page_count']} pages, {result['link_count']} links)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
