#!/usr/bin/env python3
"""Run deterministic PDF checks using PyMuPDF only."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

try:
    import pymupdf as fitz
except ImportError:  # PyMuPDF < 1.26
    import fitz  # type: ignore


def inspect(path: Path) -> dict:
    doc = fitz.open(path)
    outside: list[dict[str, object]] = []
    for page_number, page in enumerate(doc, 1):
        media = page.rect
        for word in page.get_text("words"):
            x0, y0, x1, y1, text = word[:5]
            if x0 < media.x0 - 0.5 or y0 < media.y0 - 0.5 or x1 > media.x1 + 0.5 or y1 > media.y1 + 0.5:
                outside.append({"page": page_number, "text": text, "bbox": [x0, y0, x1, y1], "media_box": [media.x0, media.y0, media.x1, media.y1]})
    return {
        "passed": not outside and len(doc) > 0,
        "page_count": len(doc),
        "outside_media_box": outside,
        "metadata": doc.metadata,
        "link_count": sum(len(page.get_links()) for page in doc),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--json", dest="json_path", type=Path)
    args = parser.parse_args()
    try:
        result = inspect(args.pdf)
    except Exception as exc:
        print(f"FAIL: PDF inspection failed: {exc}", file=sys.stderr)
        return 1
    if args.json_path:
        args.json_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not result["passed"]:
        print(f"FAIL: {len(result['outside_media_box'])} glyph boxes fall outside the media box", file=sys.stderr)
        return 1
    print(f"PASS: PDF inspection ({result['page_count']} pages, {result['link_count']} links)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
