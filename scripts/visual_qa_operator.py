#!/usr/bin/env python3
"""Compile and inspect the canonical fictional Operator theme report.

Run this in the pinned ReportKit toolchain. Successful checks write page
renders for review; they do not count as visual approval. ``--update-expected``
records a candidate image baseline and must only be used after a human has
reviewed every rendered page.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
from typing import Any, Iterable, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "latex_templates" / "examples" / "operator-report"
EXPECTED = EXAMPLE / "expected"
MINIMUM_PAGES = 6
MAXIMUM_PAGES = 8

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from publication_pipeline.scripts._bootstrap import ensure_reportkit_importable  # noqa: E402

ensure_reportkit_importable()

from publication_pipeline.scripts.publication_build import run_limited  # noqa: E402
from reportkit.diagnostics import diagnostic_envelope, inspect_log, make_diagnostic  # noqa: E402
from reportkit.toolchain import toolchain_context  # noqa: E402
from scripts.visual_qa_equity_research import compare_pages  # noqa: E402
from scripts.visual_qa_executive import render_pages  # noqa: E402

CHECKLIST = [
    "every page, including the diff continuation, has intentional composition",
    "the 9-column capability grid and each booktabs table are readable and unclipped",
    "product chips, price pills, status marks, and callout cards align with surrounding text",
    "ordinary prose, tables, captions, and callout text use Latin Modern Sans; execution lines use Latin Modern Mono",
    "terminal glyphs are light on a dark surface and diff bands continue cleanly over the page break",
    "Figures 3, 5, and 6 are legible in grayscale and have no clipped labels",
    "there are no blank pages, collisions, or excessive empty areas",
]

_OVERFULL_LINE = re.compile(r"Overfull\s+\\hbox\b", re.IGNORECASE)
_OVERFULL_PAGE = re.compile(r"Overfull\s+\\vbox\b", re.IGNORECASE)


def parse_log_issues(log_text: str) -> list[str]:
    """Return blocking layout warnings required by the Operator fixture gate.

    This parser is deliberately pure so synthetic TeX logs can exercise the
    contract without starting TeX or rendering a PDF.
    """
    issues: list[str] = []
    for line_number, line in enumerate(log_text.splitlines(), 1):
        if _OVERFULL_LINE.search(line):
            issues.append(f"line {line_number}: {line.strip()}")
        if _OVERFULL_PAGE.search(line):
            issues.append(f"line {line_number}: {line.strip()}")
        lowered = line.casefold()
        if "fancyhdr" in lowered and "headheight" in lowered and ("too small" in lowered or "increase it" in lowered):
            issues.append(f"line {line_number}: {line.strip()}")
    return issues


def _font_family(font_name: str) -> str:
    normalized = re.sub(r"[^a-z0-9]", "", font_name.casefold())
    if "lmsans" in normalized or "latinmodernsans" in normalized:
        return "sans"
    if "lmmono" in normalized or "lmtt" in normalized or "latinmodernmono" in normalized:
        return "mono"
    if "lmroman" in normalized or "latinmodernroman" in normalized:
        return "roman"
    return "other"


def check_font_regions(
    chars: Iterable[Mapping[str, Any]],
    regions: Sequence[Mapping[str, Any]],
) -> list[str]:
    """Check each non-space PDF character against its region's font family.

    A region has ``page``, ``x0``, ``top``, ``x1``, ``bottom``, ``name``, and
    ``expected_font`` keys (``sans``, ``roman``, or ``mono``). Character
    mappings use pdfplumber's coordinate keys and may include a zero-based
    ``page`` index when the input contains multiple pages.
    """
    characters = list(chars)
    problems: list[str] = []
    for region in regions:
        expected = str(region["expected_font"])
        matching = [
            char for char in characters
            if char.get("page", region.get("page")) == region.get("page")
            and not str(char.get("text", "")).isspace()
            and float(char.get("x1", 0)) > float(region["x0"])
            and float(char.get("x0", 0)) < float(region["x1"])
            and float(char.get("bottom", 0)) > float(region["top"])
            and float(char.get("top", 0)) < float(region["bottom"])
        ]
        if not matching:
            problems.append(f"{region['name']}: no text glyphs found in the expected region")
            continue
        wrong = [char for char in matching if _font_family(str(char.get("fontname", ""))) != expected]
        if wrong:
            sample = sorted({str(char.get("fontname", "unknown")) for char in wrong})[:5]
            problems.append(
                f"{region['name']}: expected Latin Modern {expected}, found {', '.join(sample)}"
            )
    return problems


def check_terminal_contrast(pixels: Any, *, minimum_glyph_pixels: int = 4) -> dict[str, Any]:
    """Measure dark background and light glyph pixels in a rendered crop.

    ``pixels`` is a NumPy grayscale or RGB(A) array. The median luminance
    represents the box background; high-luminance pixels are the visible
    glyph sample. Values use normalized sRGB luminance in [0, 1].
    """
    import numpy as np

    array = np.asarray(pixels)
    if array.size == 0 or array.ndim not in {2, 3}:
        return {"passed": False, "reason": "terminal crop is empty or has an unsupported shape"}
    values = array.astype(float)
    if float(np.max(values)) > 1.0:
        values /= 255.0
    if values.ndim == 2:
        luminance = values
    else:
        rgb = values[..., :3]
        linear = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
        luminance = linear[..., 0] * 0.2126 + linear[..., 1] * 0.7152 + linear[..., 2] * 0.0722
    background = float(np.median(luminance))
    glyphs = luminance[luminance >= 0.8]
    glyph_mean = float(glyphs.mean()) if glyphs.size else 0.0
    passed = background <= 0.15 and glyphs.size >= minimum_glyph_pixels and glyph_mean >= 0.8
    return {
        "passed": bool(passed),
        "background_luminance": background,
        "glyph_luminance": glyph_mean,
        "glyph_pixel_count": int(glyphs.size),
    }


def _template_paths() -> list[Path]:
    templates = ROOT / "latex_templates"
    return (
        sorted(templates.glob("*.cls"))
        + sorted(templates.glob("*.def"))
        + sorted(templates.glob("reportkit-*.tex"))
        + sorted(templates.glob("*.sty"))
        + sorted((templates / "themes").glob("*.sty"))
        + sorted((templates / "publication_types").glob("*.sty"))
    )


def compile_fixture(workdir: Path) -> tuple[Path, str, int]:
    """Stage the canonical fixture, generate charts, and run pdflatex twice."""
    for source in _template_paths():
        shutil.copy2(source, workdir / source.name)
    shutil.copy2(EXAMPLE / "report.tex", workdir / "report.tex")
    shutil.copy2(EXAMPLE / "figures.py", workdir / "figures.py")
    environment = {
        **os.environ,
        "LC_ALL": "C",
        "openin_any": "a",
        "openout_any": "p",
        "PYTHONPATH": str(ROOT / "python_scripts"),
        "MPLBACKEND": "Agg",
        "SOURCE_DATE_EPOCH": "1",
        "FORCE_SOURCE_DATE": "1",
        "TZ": "UTC",
    }
    figures = run_limited(
        [sys.executable, "figures.py"], cwd=workdir, capture_output=True,
        text=True, timeout=120, memory_limit_mb=2048, env=environment,
    )
    chunks = [figures.stdout + "\n" + figures.stderr]
    if figures.returncode:
        return workdir / "report.pdf", "\n".join(chunks), figures.returncode

    code = 0
    for _ in range(2):
        result = run_limited(
            ["pdflatex", "-file-line-error", "-interaction=nonstopmode", "-halt-on-error", "report.tex"],
            cwd=workdir, capture_output=True, text=True, timeout=240,
            memory_limit_mb=2048,
            env={**environment, "SOURCE_DATE_EPOCH": "1", "FORCE_SOURCE_DATE": "1"},
        )
        code = result.returncode
        chunks.append(result.stdout + "\n" + result.stderr)
        if code:
            break
    return workdir / "report.pdf", "\n".join(chunks), code


def _anchor_rect(page: Any, text: str):
    matches = page.search_for(text)
    if not matches:
        return None
    import pymupdf

    rect = pymupdf.Rect(matches[0])
    for match in matches[1:]:
        rect |= match
    return rect


def _same_page_region(document: Any, start_text: str, end_text: str, name: str, family: str) -> tuple[dict[str, Any] | None, str | None]:
    start = end = None
    start_index = end_index = None
    for page_index, page in enumerate(document):
        if start is None:
            candidate = _anchor_rect(page, start_text)
            if candidate is not None:
                start, start_index = candidate, page_index
        if end is None:
            candidate = _anchor_rect(page, end_text)
            if candidate is not None:
                end, end_index = candidate, page_index
    if start is None or end is None:
        missing = start_text if start is None else end_text
        return None, f"could not find font-region anchor {missing!r}"
    if start_index != end_index or end.y1 < start.y0:
        return None, f"font-region anchors for {name!r} are not in reading order on one page"
    page = document[start_index]
    return {
        "page": start_index,
        "x0": 42.0,
        "top": max(0.0, start.y0 - 1.5),
        "x1": float(page.rect.width - 42.0),
        "bottom": min(float(page.rect.height), end.y1 + 1.5),
        "name": name,
        "expected_font": family,
    }, None


def _spanning_regions(
    document: Any,
    start_text: str,
    end_text: str,
    name: str,
    family: str,
    *,
    require_page_break: bool = False,
) -> tuple[list[dict[str, Any]], str | None]:
    start = end = None
    start_index = end_index = None
    for page_index, page in enumerate(document):
        if start is None:
            candidate = _anchor_rect(page, start_text)
            if candidate is not None:
                start, start_index = candidate, page_index
        if end is None:
            candidate = _anchor_rect(page, end_text)
            if candidate is not None:
                end, end_index = candidate, page_index
    if start is None or end is None or start_index is None or end_index is None or end_index < start_index:
        missing = start_text if start is None else end_text
        return [], f"could not locate ordered execution font anchors near {missing!r}"
    if require_page_break and start_index == end_index:
        return [], f"{name} is expected to continue across a page boundary"
    regions: list[dict[str, Any]] = []
    for page_index in range(start_index, end_index + 1):
        page = document[page_index]
        top = start.y0 - 2.0 if page_index == start_index else 42.0
        bottom = end.y1 + 2.0 if page_index == end_index else page.rect.height - 42.0
        regions.append({
            "page": page_index,
            "x0": 52.0,
            "top": max(0.0, top),
            "x1": float(page.rect.width - 52.0),
            "bottom": min(float(page.rect.height), bottom),
            "name": f"{name} page {page_index + 1}",
            "expected_font": family,
        })
    return regions, None


def rendered_font_regions(pdf: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    """Return table/body/execution font regions measured from PDF text anchors."""
    import pdfplumber
    import pymupdf

    regions: list[dict[str, Any]] = []
    errors: list[str] = []
    with pymupdf.open(pdf) as document:
        for start, end, name in (
            ("Execution and support boundary", "90-day event history", "Table 1 product packages"),
            ("Setup (min)", "Partial", "Table 2 deployment envelope"),
            ("Review minutes", "Credit-cap month", "Table 3 run assumptions"),
        ):
            region, error = _same_page_region(document, start, end, name, "sans")
            if error:
                errors.append(error)
            elif region:
                regions.append(region)
        region, error = _same_page_region(
            document,
            "This fictional evaluation compares",
            "on a vendor dashboard.",
            "body prose sample",
            "sans",
        )
        if error:
            errors.append(error)
        elif region:
            regions.append(region)
        terminal, error = _spanning_regions(
            document,
            "loom inspect",
            "Review the patch before approving an execution token.",
            "terminal text",
            "mono",
        )
        if error:
            errors.append(error)
        regions.extend(terminal)
        diff, error = _spanning_regions(
            document,
            "@@ -1,18 +1,24 @@",
            "next-step: inspect-rendered-pages",
            "diff text",
            "mono",
            require_page_break=True,
        )
        if error:
            errors.append(error)
        regions.extend(diff)

    with pdfplumber.open(pdf) as document:
        chars: list[dict[str, Any]] = []
        for page_index, page in enumerate(document.pages):
            chars.extend({**char, "page": page_index} for char in page.chars)
    return regions, chars, errors


def _dark_surface_rect(page: Any, title_rect: Any, fallback: Any):
    import pymupdf

    candidates = []
    for drawing in page.get_drawings():
        fill = drawing.get("fill")
        rect = pymupdf.Rect(drawing.get("rect"))
        if not fill or len(fill) < 3 or not rect.contains(title_rect):
            continue
        luminance = 0.2126 * fill[0] + 0.7152 * fill[1] + 0.0722 * fill[2]
        if luminance <= 0.15 and rect.width > 100 and rect.height > 35:
            candidates.append(rect)
    return min(candidates, key=lambda rect: rect.width * rect.height) if candidates else fallback


def inspect_terminal_pixels(pdf: Path, dpi: int = 140) -> dict[str, Any]:
    """Render the terminal panel crop and measure its text/background contrast."""
    import numpy as np
    import pymupdf

    with pymupdf.open(pdf) as document:
        for page_number, page in enumerate(document, 1):
            title = _anchor_rect(page, "Fictional rehearsal")
            if title is None:
                continue
            first = _anchor_rect(page, "loom inspect")
            last = _anchor_rect(page, "Review the patch before approving an execution token.")
            if first is None or last is None:
                return {"passed": False, "reason": "terminal body anchors were not found", "page": page_number}
            fallback = pymupdf.Rect(
                max(0, title.x0 - 16),
                max(0, title.y0 - 10),
                min(page.rect.width, page.rect.width - 45),
                min(page.rect.height, last.y1 + 9),
            )
            crop = _dark_surface_rect(page, title, fallback)
            pixmap = page.get_pixmap(
                matrix=pymupdf.Matrix(dpi / 72.0, dpi / 72.0),
                clip=crop,
                colorspace=pymupdf.csRGB,
                alpha=False,
            )
            array = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(pixmap.height, pixmap.width, pixmap.n)
            result = check_terminal_contrast(array)
            result["page"] = page_number
            result["crop"] = [round(value, 2) for value in crop]
            return result
    return {"passed": False, "reason": "terminal title was not found"}


def inspect_fixture(pdf: Path, log_text: str) -> dict[str, Any]:
    import pymupdf

    diagnostics = list(inspect_log(log_text)["diagnostics"])
    layout_issues = parse_log_issues(log_text)
    hbox_diagnostics = [item for item in diagnostics if item.get("type") == "overfull_hbox"]
    hbox_index = 0
    for issue in layout_issues:
        if "Overfull" in issue and r"\hbox" in issue:
            if hbox_index < len(hbox_diagnostics):
                hbox_diagnostics[hbox_index]["severity"] = "error"
                hbox_diagnostics[hbox_index]["blocking"] = True
                hbox_index += 1
                continue
        # AC2 is stricter than the shared log policy: every overfull box and
        # small-headheight warning blocks this fixture's visual QA.
        diagnostics.append(make_diagnostic(
            "pdf_geometry",
            issue,
            code="RK_OPERATOR_LAYOUT_WARNING",
            severity="error",
        ))

    with pymupdf.open(pdf) as document:
        page_count = len(document)
        page_sizes = [
            {
                "width_mm": round(page.rect.width * 25.4 / 72.0, 3),
                "height_mm": round(page.rect.height * 25.4 / 72.0, 3),
            }
            for page in document
        ]
        blank_pages = [number for number, page in enumerate(document, 1) if not page.get_text().strip()]
        metadata = dict(document.metadata or {})
    if not MINIMUM_PAGES <= page_count <= MAXIMUM_PAGES:
        diagnostics.append(make_diagnostic(
            "pdf_geometry",
            f"operator fixture has {page_count} pages; expected {MINIMUM_PAGES}–{MAXIMUM_PAGES}",
            code="RK_OPERATOR_PAGE_COUNT",
        ))
    if any(abs(size["width_mm"] - 210) > 0.4 or abs(size["height_mm"] - 297) > 0.4 for size in page_sizes):
        diagnostics.append(make_diagnostic("pdf_geometry", "operator fixture pages must use A4 geometry", code="RK_OPERATOR_GEOMETRY"))
    if blank_pages:
        diagnostics.append(make_diagnostic("blank_page", f"blank operator pages: {blank_pages}", code="RK_OPERATOR_BLANK_PAGE"))

    font_regions, chars, region_errors = rendered_font_regions(pdf)
    for error in region_errors:
        diagnostics.append(make_diagnostic("pdf_accessibility", error, code="RK_OPERATOR_FONT_REGION"))
    for error in check_font_regions(chars, font_regions):
        diagnostics.append(make_diagnostic("pdf_accessibility", error, code="RK_OPERATOR_FONT_FAMILY"))

    contrast = inspect_terminal_pixels(pdf)
    if not contrast.get("passed"):
        diagnostics.append(make_diagnostic(
            "pdf_accessibility",
            "terminal text/background contrast did not meet the light-on-dark threshold",
            code="RK_OPERATOR_TERMINAL_CONTRAST",
            details=contrast,
        ))

    return diagnostic_envelope(
        diagnostics,
        passed=not any(item.get("severity") == "error" for item in diagnostics),
        page_count=page_count,
        page_sizes=page_sizes,
        blank_pages=blank_pages,
        metadata=metadata,
        font_regions=font_regions,
        terminal_contrast=contrast,
        manual_review=CHECKLIST,
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
    parser.add_argument("--update-expected", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "build" / "operator-qa")
    parser.add_argument("--dpi", type=int, default=140)
    parser.add_argument("--threshold", type=float, default=0.01)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if shutil.which("pdflatex") is None:
        return _skip("pdflatex not found; Operator visual QA was not compiled", args.json)
    try:
        import numpy  # noqa: F401
        import pdfplumber  # noqa: F401
        import pymupdf  # noqa: F401
    except ImportError as exc:
        return _skip(f"PDF inspection dependencies are unavailable ({exc})", args.json)

    toolchain = toolchain_context(ROOT)
    resolved = toolchain["resolved"]
    fingerprint = toolchain["fingerprint"]
    if resolved.get("status") != "pinned" or resolved.get("fingerprint") != fingerprint:
        result = diagnostic_envelope([
            make_diagnostic(
                "toolchain_mismatch",
                "Operator visual QA requires the pinned ReportKit toolchain",
                code="RK_OPERATOR_TOOLCHAIN",
            ),
        ], passed=False)
    else:
        baseline_path = EXPECTED / "baseline.json"
        baseline = json.loads(baseline_path.read_text(encoding="utf-8")) if baseline_path.exists() else None
        if not args.update_expected and (
            baseline is None
            or baseline.get("toolchain_fingerprint") != fingerprint
            or baseline.get("dpi") != args.dpi
            or baseline.get("pixel_difference_threshold") != args.threshold
        ):
            result = diagnostic_envelope([
                make_diagnostic(
                    "toolchain_mismatch",
                    "Operator visual baseline is missing or uses different settings",
                    code="RK_OPERATOR_BASELINE",
                ),
            ], passed=False)
        else:
            args.output_dir.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix="reportkit-operator-") as temporary:
                pdf, log_text, returncode = compile_fixture(Path(temporary))
                if returncode or not pdf.exists():
                    result = diagnostic_envelope([
                        make_diagnostic(
                            "compile_failure",
                            "pdflatex could not compile the Operator fixture",
                            code="RK_OPERATOR_COMPILE",
                            details={"log_tail": log_text[-6000:]},
                        ),
                    ], passed=False)
                else:
                    result = inspect_fixture(pdf, log_text)
                    if result["passed"]:
                        pages = render_pages(pdf, args.output_dir, args.dpi)
                        if args.update_expected:
                            EXPECTED.mkdir(parents=True, exist_ok=True)
                            for old in EXPECTED.glob("page-*.png"):
                                old.unlink()
                            for page in pages:
                                shutil.copy2(page, EXPECTED / page.name)
                            baseline_path.write_text(json.dumps({
                                "schema_version": 1,
                                "fixture": str(EXAMPLE.relative_to(ROOT) / "report.tex"),
                                "engine": "pdflatex",
                                "class_options": ["theme=operator", "publication-type=technical-report"],
                                "toolchain_fingerprint": fingerprint,
                                "expected_toolchain_fingerprint": fingerprint,
                                "resolved_toolchain_fingerprint": resolved.get("fingerprint"),
                                "dpi": args.dpi,
                                "pixel_difference_threshold": args.threshold,
                                "page_count": result["page_count"],
                                "page_sizes": result["page_sizes"],
                                "metadata": result["metadata"],
                                "pdf_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
                                "pages": [page.name for page in pages],
                                "visual_review": "pending",
                            }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                            result["updated"] = True
                            result["visual_review"] = "pending"
                        else:
                            mismatches = compare_pages(args.output_dir, EXPECTED, threshold=args.threshold)
                            if mismatches:
                                result = diagnostic_envelope([
                                    make_diagnostic("visual_regression", item, code="RK_OPERATOR_REGRESSION")
                                    for item in mismatches
                                ], passed=False)

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"{'PASS' if result['passed'] else 'FAIL'}: Operator visual QA")
        for item in result.get("diagnostics", []):
            print(f"  {item['severity']}: {item['message']}")
        if result["passed"] and not result.get("skipped"):
            print(f"  Rendered PNGs: {args.output_dir}")
            for item in CHECKLIST:
                print(f"  [ ] {item}")
            print("  Human review is still required before accepting an image baseline.")
        elif result.get("skipped"):
            print(f"  Skipped: {result.get('reason')}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
