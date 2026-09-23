#!/usr/bin/env python3
"""Compile and render the canonical venture Phase D pitch fixture.

Mirrors ``scripts/visual_qa_executive.py`` and reuses its staging, compile
and rendering helpers. The one addition is controlled branding (decision
D6): the fixture's ``publication.yaml`` brand section is resolved into the
same immutable ``EffectiveTheme`` record the publication pipeline uses, and
that record is materialized into ``reportkit-theme-overrides.tex`` next to
the direct ``report.tex`` -- the logo is staged at its root-relative path and
its SHA-256 is reported.

It also runs the Phase D critical gate: ``presentation_acceptance_test.tex``
(the shared presentation-semantic smoke document) is compiled under
``theme=executive`` and ``theme=venture`` with no other change, and the
rendered pixels must differ materially.

Visual approval is intentionally not inferred from a successful compile.

Usage::

    python3 scripts/visual_qa_venture.py --output-dir build/venture-qa
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "latex_templates" / "examples" / "venture-presentation"
SMOKE = ROOT / "latex_templates" / "examples" / "presentation_acceptance_test.tex"
EXPECTED_SLIDES = 12
# Mean absolute per-channel difference (0-255) above which two renders of the
# same smoke document count as "materially different". Anti-aliasing noise
# between identical themes is far below 1.0; two distinct visual systems sit
# well above this floor.
MATERIAL_DIFFERENCE_FLOOR = 6.0

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from publication_pipeline.scripts._bootstrap import ensure_reportkit_importable  # noqa: E402

ensure_reportkit_importable()

from publication_pipeline.scripts.publication_build import run_limited  # noqa: E402
from reportkit.config import CONFIG_NAME, load_publication_config, resolve_effective_theme  # noqa: E402
from reportkit.diagnostics import diagnostic_envelope, inspect_log, make_diagnostic  # noqa: E402
from reportkit.theme_overrides import materialize_tex_overrides, validate_tex_overrides  # noqa: E402
from scripts.visual_qa_executive import _template_files, render_pages  # noqa: E402

_ENV = {
    "LC_ALL": "C",
    "openin_any": "a",
    "openout_any": "p",
    "SOURCE_DATE_EPOCH": "1",
    "FORCE_SOURCE_DATE": "1",
    "TZ": "UTC",
}


def _stage_templates(workdir: Path) -> None:
    for source in _template_files():
        shutil.copy2(source, workdir / source.name)


def _compile(workdir: Path, name: str) -> tuple[Path, str, int]:
    chunks: list[str] = []
    returncode = 0
    for _ in range(2):
        process = run_limited(
            ["lualatex", "-file-line-error", "-interaction=nonstopmode", "-halt-on-error", name],
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=240,
            memory_limit_mb=2048,
            env={**os.environ, **_ENV},
        )
        returncode = process.returncode
        chunks.append(process.stdout + "\n" + process.stderr)
        if returncode:
            break
    return workdir / (Path(name).stem + ".pdf"), "\n".join(chunks), returncode


def stage_brand(workdir: Path) -> dict:
    """Materialize the fixture's effective theme exactly as the pipeline does."""
    config = load_publication_config(EXAMPLE / CONFIG_NAME)
    effective = resolve_effective_theme(config, source_root=EXAMPLE)
    if effective.brand.logo is not None:
        relative = effective.brand.logo.relative_to(EXAMPLE.resolve())
        (workdir / relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(effective.brand.logo, workdir / relative)
    overrides = workdir / "reportkit-theme-overrides.tex"
    if effective.configured:
        materialize_tex_overrides(effective, overrides)
        errors = validate_tex_overrides(overrides, effective)
    else:
        errors = []
    return {"effective_theme": effective.as_dict(), "override_errors": errors}


def compile_fixture(workdir: Path) -> tuple[Path, str, int, dict]:
    """Stage and compile the direct canonical venture fixture in ``workdir``."""
    _stage_templates(workdir)
    shutil.copy2(EXAMPLE / "report.tex", workdir / "report.tex")
    shutil.copytree(EXAMPLE / "fragments", workdir / "fragments", dirs_exist_ok=True)
    shutil.copytree(EXAMPLE / "figures", workdir / "figures", dirs_exist_ok=True)
    brand = stage_brand(workdir)
    pdf, log, returncode = _compile(workdir, "report.tex")
    return pdf, log, returncode, brand


def compile_smoke(workdir: Path, theme: str) -> tuple[Path, str, int]:
    """Compile the shared presentation smoke document under ``theme`` only."""
    workdir.mkdir(parents=True, exist_ok=True)
    _stage_templates(workdir)
    source = SMOKE.read_text(encoding="utf-8")
    marker = r"\documentclass[theme=executive,publication-type=presentation]{reportkit-slides}"
    if marker not in source:
        raise ValueError("smoke document no longer declares the expected executive class line")
    (workdir / "smoke.tex").write_text(
        source.replace(marker, marker.replace("theme=executive", f"theme={theme}")), encoding="utf-8"
    )
    return _compile(workdir, "smoke.tex")


def pixel_difference(first: Path, second: Path, dpi: int = 40) -> dict:
    """Return per-page mean absolute channel differences between two PDFs."""
    import pymupdf

    matrix = pymupdf.Matrix(dpi / 72.0, dpi / 72.0)
    left, right = pymupdf.open(first), pymupdf.open(second)
    pages: list[float] = []
    for page_left, page_right in zip(left, right):
        a = page_left.get_pixmap(matrix=matrix, alpha=False)
        b = page_right.get_pixmap(matrix=matrix, alpha=False)
        if (a.width, a.height) != (b.width, b.height):
            pages.append(255.0)
            continue
        total = sum(abs(x - y) for x, y in zip(a.samples, b.samples))
        pages.append(total / len(a.samples))
    result = {"page_counts": [len(left), len(right)], "per_page": pages, "mean": sum(pages) / len(pages) if pages else 0.0}
    left.close()
    right.close()
    return result


def inspect_fixture(pdf: Path, log: str, brand: dict | None = None) -> dict:
    import pymupdf

    diagnostics = list(inspect_log(log)["diagnostics"])
    document = pymupdf.open(pdf)
    page_sizes = [
        {"width_mm": round(page.rect.width * 25.4 / 72.0, 3), "height_mm": round(page.rect.height * 25.4 / 72.0, 3)}
        for page in document
    ]
    page_count = len(document)
    geometry_ok = all(abs(size["width_mm"] - 160) < 0.2 and abs(size["height_mm"] - 90) < 0.2 for size in page_sizes)
    blank_pages = [number for number, page in enumerate(document, 1) if not page.get_text().strip()]
    metadata = dict(document.metadata or {})
    document.close()
    if page_count != EXPECTED_SLIDES:
        diagnostics.append(make_diagnostic("pdf_geometry", f"venture fixture must contain {EXPECTED_SLIDES} slides; got {page_count}", code="RK_VENTURE_PAGE_COUNT"))
    if not geometry_ok:
        diagnostics.append(make_diagnostic("pdf_geometry", f"venture fixture pages must be 160 x 90 mm; got {page_sizes}", code="RK_VENTURE_CANVAS"))
    if blank_pages:
        diagnostics.append(make_diagnostic("blank_page", f"venture fixture contains blank slides: {blank_pages}", code="RK_VENTURE_BLANK_SLIDE"))
    for error in (brand or {}).get("override_errors", []):
        diagnostics.append(make_diagnostic("configuration_error", f"generated brand overrides disagree with the effective theme: {error}", code="RK_VENTURE_BRAND_SYNC"))
    expected = {
        "title": "Every chilled aisle, one step ahead of spoilage - Lumiquay seed pitch \u2013 a fictional startup",
        "author": "Lumiquay founding team",
        "subject": "Lumiquay cold-chain intelligence seed pitch",
        "keywords": "ReportKit, venture theme, pitch, fictional",
    }
    for field, wanted in expected.items():
        if str(metadata.get(field) or "").strip() != wanted:
            diagnostics.append(make_diagnostic("pdf_accessibility", f"venture fixture metadata {field!r} does not match its contract", code="RK_VENTURE_METADATA", details={"field": field, "expected": wanted, "actual": metadata.get(field)}))
    return diagnostic_envelope(
        diagnostics,
        passed=not any(item.get("severity") == "error" for item in diagnostics),
        page_count=page_count,
        page_sizes=page_sizes,
        blank_pages=blank_pages,
        metadata=metadata,
        brand=brand or {},
        manual_review=[
            "one idea per slide; display type dominates and negative space is generous",
            "opening, statement and closing frames are dark; content frames are light",
            "brand primary/secondary and logo appear consistently in slides and chart",
            "product image and hero metrics read as the subject of their slides",
            "no clipped labels, overlaps or default-theme colours",
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
    parser.add_argument("--output-dir", type=Path, default=ROOT / "build" / "venture-qa")
    parser.add_argument("--dpi", type=int, default=150)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if shutil.which("lualatex") is None:
        return _skip("lualatex not found; venture visual QA was not compiled", args.json)
    try:
        import pymupdf  # noqa: F401
    except ImportError as exc:
        return _skip(f"PyMuPDF is unavailable ({exc}); venture visual QA was not rendered", args.json)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="reportkit-venture-") as temporary:
        workdir = Path(temporary)
        fixture_dir = workdir / "fixture"
        fixture_dir.mkdir()
        pdf, log, returncode, brand = compile_fixture(fixture_dir)
        if returncode:
            result = diagnostic_envelope([
                make_diagnostic("compile_failure", "LuaLaTeX could not compile the venture fixture", code="RK_VENTURE_COMPILE", details={"tail": log[-6000:]}),
            ], passed=False)
        else:
            result = inspect_fixture(pdf, log, brand)
            if result["passed"]:
                render_pages(pdf, args.output_dir / "fixture", args.dpi)
        smoke: dict = {}
        pdfs: dict[str, Path] = {}
        for theme in ("executive", "venture"):
            smoke_pdf, smoke_log, smoke_code = compile_smoke(workdir / f"smoke-{theme}", theme)
            smoke[theme] = {"returncode": smoke_code}
            if smoke_code:
                smoke[theme]["tail"] = smoke_log[-4000:]
            else:
                pdfs[theme] = smoke_pdf
                render_pages(smoke_pdf, args.output_dir / f"smoke-{theme}", args.dpi)
        if len(pdfs) == 2:
            smoke["difference"] = pixel_difference(pdfs["executive"], pdfs["venture"])
            smoke["passed"] = (
                smoke["difference"]["page_counts"][0] == smoke["difference"]["page_counts"][1]
                and smoke["difference"]["mean"] >= MATERIAL_DIFFERENCE_FLOOR
            )
        else:
            smoke["passed"] = False
        result["smoke_gate"] = smoke
        result["passed"] = bool(result["passed"] and smoke["passed"])
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True, default=str))
    else:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"{status}: venture fixture QA ({result.get('page_count', 0)} slides)")
        for item in result.get("diagnostics", []):
            print(f"  {item['severity']}: {item['message']}")
        difference = result["smoke_gate"].get("difference", {})
        print(f"  smoke gate executive vs venture: mean pixel difference {difference.get('mean', 0):.1f} (floor {MATERIAL_DIFFERENCE_FLOOR})")
        print(f"  Rendered PNGs: {args.output_dir}")
        print("  Human visual review remains required before accepting a baseline.")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
