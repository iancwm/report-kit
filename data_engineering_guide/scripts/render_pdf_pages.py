#!/usr/bin/env python3
"""Render every page of a PDF to a PNG for visual inspection.

Usage: render_pdf_pages.py <input.pdf> <output-dir> [--dpi 150]
Writes <output-dir>/page-01.png, page-02.png, ... and a deterministic
index.html. The output directory is replaced atomically, so a shorter rerun
cannot retain stale page images.
"""
import argparse
from datetime import datetime, timezone
import html
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

try:
    import pymupdf as fitz  # PyMuPDF >= 1.26
except ImportError:  # pragma: no cover - compatibility with older environments
    import fitz  # type: ignore


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("out_dir", type=Path)
    parser.add_argument("--dpi", type=int, default=150)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()

    if not args.pdf.is_file():
        print(f"render_pdf_pages.py: no such file: {args.pdf}", file=sys.stderr)
        return 1
    if args.dpi <= 0:
        print("render_pdf_pages.py: --dpi must be positive", file=sys.stderr)
        return 1

    args.out_dir.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix=f".{args.out_dir.name}.", dir=args.out_dir.parent))
    zoom = args.dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)

    try:
        doc = fitz.open(args.pdf)
        page_files: list[str] = []
        for page_index, page in enumerate(doc, start=1):
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            out_path = temp_dir / f"page-{page_index:02d}.png"
            pixmap.save(out_path)
            page_files.append(out_path.name)
            print(f"render_pdf_pages.py: wrote {out_path}")
        page_count = len(page_files)
        doc.close()
        if page_count == 0:
            raise RuntimeError("PDF contains no pages")

        links = "\n".join(
            f'  <li><a href="{html.escape(name)}"><img src="{html.escape(name)}" '
            f'alt="Page {index}" loading="lazy"></a></li>'
            for index, name in enumerate(page_files, start=1)
        )
        (temp_dir / "index.html").write_text(
            "<!doctype html>\n"
            "<meta charset=\"utf-8\">\n"
            "<title>Guide build pages</title>\n"
            "<style>body{font:14px system-ui;margin:2rem}ol{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:1rem;padding:0;list-style-position:inside}li{border:1px solid #ddd;padding:.5rem}img{max-width:100%;height:auto}</style>\n"
            f"<h1>Guide build pages ({page_count})</h1><ol>\n{links}\n</ol>\n",
            encoding="utf-8",
        )
        manifest = {
            "page_count": page_count,
            "dpi": args.dpi,
            "pdf": args.pdf.name,
            "files": page_files,
            "index": "index.html",
            "rendered_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        (temp_dir / "pages.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if args.out_dir.exists():
            if args.out_dir.is_dir():
                shutil.rmtree(args.out_dir)
            else:
                args.out_dir.unlink()
        os.replace(temp_dir, args.out_dir)
        if args.manifest:
            args.manifest.parent.mkdir(parents=True, exist_ok=True)
            args.manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except Exception as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        print(f"render_pdf_pages.py: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
