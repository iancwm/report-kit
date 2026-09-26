#!/usr/bin/env python3
"""Compile, inspect, render, and compare the Phase E editorial fixture.

Run in the pinned Docker image. ``--update-expected`` records a candidate
baseline; review every rendered page before treating it as approved.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "latex_templates" / "examples" / "editorial-feature"
EXPECTED = EXAMPLE / "expected"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from publication_pipeline.scripts._bootstrap import ensure_reportkit_importable  # noqa: E402

ensure_reportkit_importable()

from publication_pipeline.scripts.publication_build import run_limited  # noqa: E402
from reportkit.diagnostics import diagnostic_envelope, inspect_log, make_diagnostic  # noqa: E402
from reportkit.toolchain import toolchain_context  # noqa: E402
from scripts.visual_qa_equity_research import compare_pages  # noqa: E402
from scripts.visual_qa_executive import _template_files, render_pages  # noqa: E402

CHECKLIST = [
    "drop cap and headline render cleanly on the opening page",
    "single and double columns have no orphaned prose or stranded headings",
    "both pull quotes and the sidebar clear the surrounding body text",
    "column and full-width exhibits, charts, diagram, captions, and credits fit",
    "chart labels use Libertinus Sans, matching the editorial metadata face",
    "no blank pages, clipped content, collisions, or excessive empty space",
]


def compile_fixture(workdir: Path) -> tuple[Path, str, int]:
    for source in _template_files():
        shutil.copy2(source, workdir / source.name)
    shutil.copy2(EXAMPLE / "report.tex", workdir / "report.tex")
    shutil.copy2(EXAMPLE / "figures.py", workdir / "figures.py")
    figures = run_limited(
        [sys.executable, "figures.py"], cwd=workdir, capture_output=True,
        text=True, timeout=120, memory_limit_mb=2048,
        env={**os.environ, "PYTHONPATH": str(ROOT / "python_scripts"),
             "MPLBACKEND": "Agg", "SOURCE_DATE_EPOCH": "1", "TZ": "UTC"},
    )
    if figures.returncode:
        return workdir / "report.pdf", figures.stdout + "\n" + figures.stderr, figures.returncode
    chunks = []
    code = 0
    for _ in range(2):
        result = run_limited(
            ["lualatex", "-file-line-error", "-interaction=nonstopmode", "-halt-on-error", "report.tex"],
            cwd=workdir, capture_output=True, text=True, timeout=240,
            memory_limit_mb=2048,
            env={**os.environ, "LC_ALL": "C", "openin_any": "a", "openout_any": "p",
                 "SOURCE_DATE_EPOCH": "1", "FORCE_SOURCE_DATE": "1", "TZ": "UTC"},
        )
        code = result.returncode
        chunks.append(result.stdout + "\n" + result.stderr)
        if code:
            break
    return workdir / "report.pdf", "\n".join(chunks), code


def inspect_fixture(pdf: Path, log: str) -> dict:
    import pymupdf

    diagnostics = list(inspect_log(log)["diagnostics"])
    with pymupdf.open(pdf) as document:
        sizes = [
            {"page": number, "width": page.rect.width, "height": page.rect.height}
            for number, page in enumerate(document, 1)
        ]
        blanks = [number for number, page in enumerate(document, 1) if not page.get_text().strip()]
        fonts = sorted({font[3] for page in document for font in page.get_fonts()})
        metadata = dict(document.metadata or {})
        count = len(document)
    if count != 6:
        diagnostics.append(make_diagnostic("pdf_geometry", f"editorial fixture has {count} pages; expected 6", code="RK_EDITORIAL_PAGE_COUNT"))
    if any(abs(size["width"] - 595.276) > 1 or abs(size["height"] - 841.89) > 1 for size in sizes):
        diagnostics.append(make_diagnostic("pdf_geometry", "editorial pages must use A4 geometry", code="RK_EDITORIAL_GEOMETRY"))
    if blanks:
        diagnostics.append(make_diagnostic("blank_page", f"blank editorial pages: {blanks}", code="RK_EDITORIAL_BLANK_PAGE"))
    if not any("LibertinusSans" in font for font in fonts):
        diagnostics.append(make_diagnostic("pdf_accessibility", "Libertinus Sans is absent from the PDF", code="RK_EDITORIAL_CHART_FONT"))
    for figure in sorted((pdf.parent / "figures").glob("*.pdf")):
        with pymupdf.open(figure) as chart:
            chart_fonts = {font[3] for page in chart for font in page.get_fonts()}
        if chart_fonts and not any("LibertinusSans" in name for name in chart_fonts):
            diagnostics.append(make_diagnostic("pdf_accessibility", f"{figure.name} does not use Libertinus Sans", code="RK_EDITORIAL_CHART_FONT"))
    return diagnostic_envelope(
        diagnostics, passed=not any(item["severity"] == "error" for item in diagnostics),
        page_count=count, page_dimensions=sizes, blank_pages=blanks,
        fonts=fonts, metadata=metadata, manual_review=CHECKLIST,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--update-expected", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "build" / "editorial-qa")
    parser.add_argument("--dpi", type=int, default=150)
    parser.add_argument("--threshold", type=float, default=0.01)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if shutil.which("lualatex") is None:
        result = diagnostic_envelope([], passed=True, skipped=True, reason="lualatex unavailable")
        print(json.dumps(result, indent=2) if args.json else "WARN: lualatex unavailable")
        return 0
    try:
        import numpy  # noqa: F401
        import pymupdf  # noqa: F401
    except ImportError as exc:
        result = diagnostic_envelope([], passed=True, skipped=True, reason=str(exc))
        print(json.dumps(result, indent=2) if args.json else f"WARN: {exc}")
        return 0

    toolchain = toolchain_context(ROOT)
    resolved = toolchain["resolved"]
    fingerprint = toolchain["fingerprint"]
    if resolved["status"] != "pinned" or resolved.get("fingerprint") != fingerprint:
        result = diagnostic_envelope([
            make_diagnostic("toolchain_mismatch", "editorial baseline requires the pinned toolchain", code="RK_EDITORIAL_TOOLCHAIN")
        ], passed=False)
    else:
        baseline_path = EXPECTED / "baseline.json"
        baseline = json.loads(baseline_path.read_text()) if baseline_path.exists() else None
        if not args.update_expected and (baseline is None or baseline.get("toolchain_fingerprint") != fingerprint
                                         or baseline.get("dpi") != args.dpi
                                         or baseline.get("pixel_difference_threshold") != args.threshold):
            result = diagnostic_envelope([
                make_diagnostic("toolchain_mismatch", "editorial baseline is missing or has different settings", code="RK_EDITORIAL_BASELINE")
            ], passed=False)
        else:
            with tempfile.TemporaryDirectory(prefix="reportkit-editorial-") as temporary:
                pdf, log, code = compile_fixture(Path(temporary))
                if code or not pdf.exists():
                    result = diagnostic_envelope([
                        make_diagnostic("compile_failure", "editorial fixture failed to compile", code="RK_EDITORIAL_COMPILE", details={"log_tail": log[-4000:]})
                    ], passed=False)
                else:
                    result = inspect_fixture(pdf, log)
                    if result["passed"]:
                        pages = render_pages(pdf, args.output_dir, args.dpi)
                        if args.update_expected:
                            EXPECTED.mkdir(parents=True, exist_ok=True)
                            for old in EXPECTED.glob("page-*.png"):
                                old.unlink()
                            for page in pages:
                                shutil.copy2(page, EXPECTED / page.name)
                            manifest = {
                                "schema_version": 1, "fixture": str(EXAMPLE.relative_to(ROOT) / "report.tex"),
                                "engine": "lualatex", "class_options": ["theme=editorial", "publication-type=feature-article"],
                                "toolchain_fingerprint": fingerprint,
                                "expected_toolchain_fingerprint": fingerprint,
                                "resolved_toolchain_fingerprint": resolved["fingerprint"],
                                "dpi": args.dpi, "pixel_difference_threshold": args.threshold,
                                "page_count": result["page_count"], "page_dimensions": result["page_dimensions"],
                                "fonts": result["fonts"], "metadata": result["metadata"],
                                "pdf_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
                                "pages": [page.name for page in pages],
                            }
                            baseline_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
                            result["updated"] = True
                        else:
                            mismatches = compare_pages(args.output_dir, EXPECTED, threshold=args.threshold)
                            if mismatches:
                                result = diagnostic_envelope([
                                    make_diagnostic("visual_regression", item, code="RK_EDITORIAL_REGRESSION")
                                    for item in mismatches
                                ], passed=False)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"{'PASS' if result['passed'] else 'FAIL'}: editorial visual QA")
        for item in result.get("diagnostics", []):
            print(f"  {item['severity']}: {item['message']}")
        if result["passed"]:
            print(f"  Rendered pages: {args.output_dir}")
            for item in CHECKLIST:
                print(f"  [ ] {item}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
