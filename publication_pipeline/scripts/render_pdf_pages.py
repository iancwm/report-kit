#!/usr/bin/env python3
"""Render a PDF (or a selected page range) into a fresh page directory and contact-sheet index."""
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

try:
    from _bootstrap import ensure_reportkit_importable
except ImportError:  # imported as publication_pipeline.scripts.render_pdf_pages
    from ._bootstrap import ensure_reportkit_importable

ensure_reportkit_importable()

REPO_ROOT = Path(__file__).resolve().parents[2]

from reportkit.diagnostics import diagnostic_envelope, make_diagnostic  # noqa: E402
from reportkit.toolchain import toolchain_context  # noqa: E402

try:
    import pymupdf as fitz
except ImportError:  # PyMuPDF < 1.26
    try:
        import fitz  # type: ignore
    except ImportError:
        fitz = None  # type: ignore[assignment]

# Mirrors reportkit.cli's EXIT_CONFIG/EXIT_VALIDATION/EXIT_ENVIRONMENT constants
# without importing cli.py (this script also runs standalone in a dedicated
# PDF-tooling venv that may not have the rest of the reportkit package on its
# path beyond what _bootstrap wires up).
EXIT_OK = 0
EXIT_CONFIG = 2
EXIT_VALIDATION = 3
EXIT_ENVIRONMENT = 5


def parse_page_selection(spec: str, page_count: int) -> list[int]:
    """Parse a 1-based page selection such as ``"1,3,5-7"`` into a sorted, de-duplicated list.

    Raises ``ValueError`` on malformed tokens, non-positive pages, an inverted
    range, or any page beyond ``page_count``.
    """
    pages: set[int] = set()
    for raw_token in spec.split(","):
        token = raw_token.strip()
        if not token:
            raise ValueError(f"invalid page selection: {spec!r}")
        if "-" in token:
            start_text, _, end_text = token.partition("-")
            try:
                start, end = int(start_text), int(end_text)
            except ValueError:
                raise ValueError(f"invalid page range: {token!r}") from None
            if start < 1 or end < start:
                raise ValueError(f"invalid page range: {token!r}")
            pages.update(range(start, end + 1))
        else:
            try:
                page = int(token)
            except ValueError:
                raise ValueError(f"invalid page number: {token!r}") from None
            if page < 1:
                raise ValueError(f"invalid page number: {token!r}")
            pages.add(page)
    out_of_range = sorted(page for page in pages if page > page_count)
    if out_of_range:
        raise ValueError(f"page(s) {out_of_range} exceed page count {page_count}")
    return sorted(pages)


def render(pdf: Path, out_dir: Path, *, dpi: int = 150, pages: str | None = None) -> dict:
    """Render the selected pages of ``pdf`` as PNGs into a fresh ``out_dir``.

    ``pages`` selects a subset (see ``parse_page_selection``); omitted, every
    page renders, matching the original full-document behaviour.
    """
    if fitz is None:
        raise ModuleNotFoundError("PyMuPDF is not installed")
    if dpi <= 0:
        raise ValueError("--dpi must be positive")
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix=f".{out_dir.name}.", dir=out_dir.parent))
    try:
        doc = fitz.open(pdf)
        try:
            total_pages = doc.page_count
            if total_pages < 1:
                raise RuntimeError("PDF contains no pages")
            selected = parse_page_selection(pages, total_pages) if pages else list(range(1, total_pages + 1))
            files: list[str] = []
            matrix = fitz.Matrix(dpi / 72.0, dpi / 72.0)
            for number in selected:
                filename = f"page-{number:02d}.png"
                doc[number - 1].get_pixmap(matrix=matrix, alpha=False).save(temp_dir / filename)
                files.append(filename)
        finally:
            doc.close()
        links = "\n".join(
            f'<li><a href="{html.escape(name)}"><img src="{html.escape(name)}" alt="{html.escape(name)}"></a></li>'
            for name in files
        )
        (temp_dir / "index.html").write_text(
            '<!doctype html><meta charset="utf-8"><title>ReportKit pages</title>'
            '<style>body{font:14px system-ui;margin:2rem}ol{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:1rem;padding:0}li{border:1px solid #ddd;padding:.5rem}img{max-width:100%}</style>'
            f"<h1>Pages ({len(files)} of {total_pages})</h1><ol>{links}</ol>\n",
            encoding="utf-8",
        )
        manifest = {
            "page_count": total_pages,
            "rendered_pages": selected,
            "dpi": dpi,
            "pdf": pdf.name,
            "files": files,
            "index": "index.html",
            "rendered_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "toolchain_fingerprint": toolchain_context(REPO_ROOT)["fingerprint"],
        }
        (temp_dir / "pages.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if out_dir.exists():
            if out_dir.is_dir():
                shutil.rmtree(out_dir)
            else:
                out_dir.unlink()
        os.replace(temp_dir, out_dir)
    except BaseException:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("out_dir", type=Path)
    parser.add_argument("--dpi", type=int, default=150)
    parser.add_argument("--pages", help="page selection, e.g. '1,3,5-7' (default: every page)")
    parser.add_argument("--manifest", type=Path, help="also write the manifest to this path")
    parser.add_argument("--json", dest="json_path", type=Path, help="write a diagnostic-envelope result to this path")
    args = parser.parse_args()

    def write_json(result: dict) -> None:
        if args.json_path:
            args.json_path.parent.mkdir(parents=True, exist_ok=True)
            args.json_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if not args.pdf.is_file():
        message = f"missing PDF: {args.pdf}"
        write_json(diagnostic_envelope([make_diagnostic("configuration_error", message, code="RK_RENDER_PDF_MISSING")], passed=False))
        print(message, file=sys.stderr)
        return EXIT_CONFIG

    try:
        manifest = render(args.pdf, args.out_dir, dpi=args.dpi, pages=args.pages)
    except ModuleNotFoundError as exc:
        message = f"PDF rendering requires PyMuPDF: {exc}"
        write_json(diagnostic_envelope([make_diagnostic("environment_error", message, code="RK_PYMUPDF_MISSING")], passed=False))
        print(f"render_pdf_pages.py: {message}", file=sys.stderr)
        return EXIT_ENVIRONMENT
    except ValueError as exc:
        write_json(diagnostic_envelope([make_diagnostic("configuration_error", str(exc), code="RK_RENDER_PAGES_INVALID")], passed=False))
        print(f"render_pdf_pages.py: {exc}", file=sys.stderr)
        return EXIT_CONFIG
    except Exception as exc:
        write_json(diagnostic_envelope([make_diagnostic("pdf_geometry", str(exc), code="RK_RENDER_FAILED")], passed=False))
        print(f"render_pdf_pages.py: {exc}", file=sys.stderr)
        return EXIT_VALIDATION

    if args.manifest:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_json(diagnostic_envelope([], passed=True, out_dir=str(args.out_dir), **manifest))
    print(f"PASS: rendered {len(manifest['files'])} of {manifest['page_count']} page(s) to {args.out_dir} (dpi={args.dpi})")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
