#!/usr/bin/env python3
"""Render every page of a PDF to a PNG for visual inspection.

Usage: render_pdf_pages.py <input.pdf> <output-dir> [--dpi 150]
Writes <output-dir>/page-01.png, page-02.png, ...
"""
import argparse
import sys
from pathlib import Path

import fitz  # PyMuPDF


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("out_dir", type=Path)
    parser.add_argument("--dpi", type=int, default=150)
    args = parser.parse_args()

    if not args.pdf.is_file():
        print(f"render_pdf_pages.py: no such file: {args.pdf}", file=sys.stderr)
        return 1

    args.out_dir.mkdir(parents=True, exist_ok=True)
    zoom = args.dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)

    doc = fitz.open(args.pdf)
    for page_index, page in enumerate(doc, start=1):
        pixmap = page.get_pixmap(matrix=matrix)
        out_path = args.out_dir / f"page-{page_index:02d}.png"
        pixmap.save(out_path)
        print(f"render_pdf_pages.py: wrote {out_path}")
    doc.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
