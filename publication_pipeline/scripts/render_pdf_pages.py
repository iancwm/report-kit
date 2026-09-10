#!/usr/bin/env python3
"""Render a PDF into a fresh page directory and contact-sheet index."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import os
import shutil
import sys
import tempfile

REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON_ROOT = REPO_ROOT / "python_scripts"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from reportkit.toolchain import toolchain_context  # noqa: E402

try:
    import pymupdf as fitz
except ImportError:  # PyMuPDF < 1.26
    import fitz  # type: ignore


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("out_dir", type=Path)
    parser.add_argument("--dpi", type=int, default=150)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    if not args.pdf.is_file():
        print(f"missing PDF: {args.pdf}", file=sys.stderr)
        return 1
    if args.dpi <= 0:
        print("--dpi must be positive", file=sys.stderr)
        return 1
    args.out_dir.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix=f".{args.out_dir.name}.", dir=args.out_dir.parent))
    try:
        doc = fitz.open(args.pdf)
        files: list[str] = []
        matrix = fitz.Matrix(args.dpi / 72.0, args.dpi / 72.0)
        for number, page in enumerate(doc, 1):
            filename = f"page-{number:02d}.png"
            page.get_pixmap(matrix=matrix, alpha=False).save(temp_dir / filename)
            files.append(filename)
        page_count = len(files)
        doc.close()
        if not page_count:
            raise RuntimeError("PDF contains no pages")
        links = "\n".join(f'<li><a href="{html.escape(name)}"><img src="{html.escape(name)}" alt="Page {number}"></a></li>' for number, name in enumerate(files, 1))
        (temp_dir / "index.html").write_text(
            '<!doctype html><meta charset="utf-8"><title>ReportKit pages</title>'
            '<style>body{font:14px system-ui;margin:2rem}ol{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:1rem;padding:0}li{border:1px solid #ddd;padding:.5rem}img{max-width:100%}</style>'
            f"<h1>Pages ({page_count})</h1><ol>{links}</ol>\n",
            encoding="utf-8",
        )
        manifest = {
            "page_count": page_count,
            "dpi": args.dpi,
            "pdf": args.pdf.name,
            "files": files,
            "index": "index.html",
            "rendered_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "toolchain_fingerprint": toolchain_context(REPO_ROOT)["fingerprint"],
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
