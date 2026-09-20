#!/usr/bin/env python3
"""Compile and render the canonical executive Phase C slide fixture.

This automates the deterministic parts of executive-theme QA: target selection,
ten-slide output, 160 x 90 mm canvas geometry, missing assets, undefined
references, and overfull content. It also writes page PNGs for human review;
visual approval is intentionally not inferred from a successful compilation.

Usage::

    python3 scripts/visual_qa_executive.py --output-dir build/executive-qa

The command exits zero with a structured warning when LuaLaTeX or PyMuPDF is
not available, matching the repository's other visual-QA helpers.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "latex_templates" / "examples" / "executive-presentation"
TEMPLATES = ROOT / "latex_templates"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from publication_pipeline.scripts._bootstrap import ensure_reportkit_importable

ensure_reportkit_importable()

from publication_pipeline.scripts.publication_build import run_limited
from reportkit.diagnostics import diagnostic_envelope, inspect_log, make_diagnostic


def _template_files() -> list[Path]:
    return (
        sorted(TEMPLATES.glob("*.cls"))
        + sorted(TEMPLATES.glob("*.def"))
        + sorted(TEMPLATES.glob("reportkit-*.tex"))
        + sorted(TEMPLATES.glob("*.sty"))
        + sorted((TEMPLATES / "themes").glob("*.sty"))
        + sorted((TEMPLATES / "publication_types").glob("*.sty"))
    )


def compile_fixture(workdir: Path) -> tuple[Path, str, int]:
    """Stage and compile the direct canonical fixture in ``workdir``."""
    for source in _template_files():
        shutil.copy2(source, workdir / source.name)
    shutil.copy2(EXAMPLE / "report.tex", workdir / "report.tex")
    shutil.copytree(EXAMPLE / "fragments", workdir / "fragments", dirs_exist_ok=True)
    shutil.copytree(EXAMPLE / "figures", workdir / "figures", dirs_exist_ok=True)

    chunks: list[str] = []
    returncode = 0
    for _ in range(2):
        process = run_limited(
            ["lualatex", "-file-line-error", "-interaction=nonstopmode", "-halt-on-error", "report.tex"],
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=180,
            memory_limit_mb=2048,
            env={
                **os.environ,
                "openin_any": "a",
                "openout_any": "p",
                "SOURCE_DATE_EPOCH": "1",
                "FORCE_SOURCE_DATE": "1",
                "TZ": "UTC",
            },
        )
        returncode = process.returncode
        chunks.append(process.stdout + "\n" + process.stderr)
        if returncode:
            break
    return workdir / "report.pdf", "\n".join(chunks), returncode


def render_pages(pdf: Path, output_dir: Path, dpi: int) -> list[Path]:
    import pymupdf

    output_dir.mkdir(parents=True, exist_ok=True)
    matrix = pymupdf.Matrix(dpi / 72.0, dpi / 72.0)
    paths: list[Path] = []
    document = pymupdf.open(pdf)
    for number, page in enumerate(document, 1):
        output = output_dir / f"page-{number:02d}.png"
        page.get_pixmap(matrix=matrix, alpha=False).save(output)
        paths.append(output)
    document.close()
    return paths


def inspect_fixture(pdf: Path, log: str) -> dict:
    import pymupdf

    diagnostics = list(inspect_log(log)["diagnostics"])
    document = pymupdf.open(pdf)
    page_sizes = [
        {"width_mm": round(page.rect.width * 25.4 / 72.0, 3), "height_mm": round(page.rect.height * 25.4 / 72.0, 3)}
        for page in document
    ]
    page_count = len(document)
    geometry_ok = all(
        abs(size["width_mm"] - 160) < 0.2 and abs(size["height_mm"] - 90) < 0.2
        for size in page_sizes
    )
    text_lengths = [len(page.get_text().strip()) for page in document]
    blank_pages = [number for number, length in enumerate(text_lengths, 1) if length == 0]
    metadata = dict(document.metadata or {})
    document.close()
    if page_count != 10:
        diagnostics.append(make_diagnostic("pdf_geometry", f"executive fixture must contain 10 slides; got {page_count}", code="RK_EXECUTIVE_PAGE_COUNT"))
    if not geometry_ok:
        diagnostics.append(make_diagnostic("pdf_geometry", f"executive fixture pages must be 160 x 90 mm; got {page_sizes}", code="RK_EXECUTIVE_CANVAS"))
    if blank_pages:
        diagnostics.append(make_diagnostic("blank_page", f"executive fixture contains blank slides: {blank_pages}", code="RK_EXECUTIVE_BLANK_SLIDE"))
    expected = {
        "title": "Turn fragmented operational data into decision velocity - A fictional technology strategy review",
        "author": "NexaGrid Strategy Office",
        "subject": "NexaGrid decision velocity strategy",
        "keywords": "ReportKit, executive theme, strategy, fictional",
    }
    for field, wanted in expected.items():
        if str(metadata.get(field) or "").strip() != wanted:
            diagnostics.append(make_diagnostic("pdf_accessibility", f"executive fixture metadata {field!r} does not match its contract", code="RK_EXECUTIVE_METADATA", details={"field": field, "expected": wanted, "actual": metadata.get(field)}))
    return diagnostic_envelope(
        diagnostics,
        passed=not any(item.get("severity") == "error" for item in diagnostics),
        page_count=page_count,
        page_sizes=page_sizes,
        blank_pages=blank_pages,
        metadata=metadata,
        manual_review=[
            "assertion is the first read on every content slide",
            "charts, tables, and diagrams have no overlap or clipped labels",
            "palette reads as restrained navy/teal with a warm decision accent",
            "font family is consistent between TeX text and the generated chart",
            "no default-theme blue or decorative navigation leaks into the deck",
        ],
    )


def _skip(message: str, as_json: bool) -> int:
    result = diagnostic_envelope([], passed=True, skipped=True, reason=message)
    if as_json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"WARN: {message}", file=sys.stderr)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "build" / "executive-qa")
    parser.add_argument("--dpi", type=int, default=150)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if shutil.which("lualatex") is None:
        return _skip("lualatex not found; executive visual QA was not compiled", args.json)
    try:
        import pymupdf  # noqa: F401
    except ImportError as exc:
        return _skip(f"PyMuPDF is unavailable ({exc}); executive visual QA was not rendered", args.json)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="reportkit-executive-") as temporary:
        pdf, log, returncode = compile_fixture(Path(temporary))
        if returncode:
            result = diagnostic_envelope([
                make_diagnostic("compile_failure", "LuaLaTeX could not compile the executive fixture", code="RK_EXECUTIVE_COMPILE", details={"tail": log[-6000:]}),
            ], passed=False)
        else:
            result = inspect_fixture(pdf, log)
            if result["passed"]:
                render_pages(pdf, args.output_dir, args.dpi)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"{status}: executive fixture QA ({result.get('page_count', 0)} slides)")
        if result.get("diagnostics"):
            for item in result["diagnostics"]:
                print(f"  {item['severity']}: {item['message']}")
        if result["passed"]:
            print(f"  Rendered PNGs: {args.output_dir}")
            print("  Human visual review remains required before accepting a baseline.")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
