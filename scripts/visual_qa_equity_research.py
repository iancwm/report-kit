#!/usr/bin/env python3
"""Visual-regression QA for the equity-research example fixture.

Spec section 25 ("Visual regression testing") of
docs/superpowers/specs/2026-09-09-reportkit-institutional-theme-and-equity-profile-spec.md
asks for PNG previews of canonical pages compared in CI/QA, plus a
checklist covering geometry, headline wrapping, sidebar alignment,
exhibit positioning, chart fonts, table overflow, source alignment,
blank pages, and overfull boxes. This script automates what can be
automated -- compiling
latex_templates/examples/equity-research/report.tex, running ReportKit's
own log diagnostics (reportkit.diagnostics.inspect_log) for overfull/
underfull boxes and undefined references, rendering every page to PNG,
and pixel-diffing against the checked-in expected/ baseline -- and prints
the rest of spec section 25's checklist as an explicit manual-review
reminder, since layout correctness and chart-font *identity* (as opposed
to whether the log recorded a font substitution) still need a human
looking at the render. Spec section 25's own words: "Where programmatic
font detection is unreliable, the render should still be included in
visual QA."

Requires lualatex (the institutional-research theme's engine requirement,
spec section 4) plus PyMuPDF and NumPy. Exits 0 and prints a WARN, same
convention as scripts/acceptance_check.sh, when either is unavailable --
this is a QA aid, not a blocking gate by itself. The implementation
session that wrote this script had neither lualatex nor (initially)
PyMuPDF/NumPy available -- see the institutional-theme implementation
plan's Step 5 section for exactly what could and could not be exercised
here, and run this for real on a machine with both before trusting its
PASS.

Usage:
    python3 scripts/visual_qa_equity_research.py [--update-expected] [--dpi 150] [--threshold 0.01]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "latex_templates" / "examples" / "equity-research"
EXPECTED = EXAMPLE / "expected"
TEMPLATES = ROOT / "latex_templates"

sys.path.insert(0, str(ROOT / "python_scripts"))
sys.path.insert(0, str(ROOT / "publication_pipeline" / "scripts"))

from reportkit.diagnostics import diagnostic_envelope, make_diagnostic  # noqa: E402
from reportkit.toolchain import toolchain_context  # noqa: E402
from publication_build import run_limited  # noqa: E402


def _warn_exit0(message: str, *, as_json: bool = False) -> int:
    if as_json:
        print(json.dumps(diagnostic_envelope([], passed=True, skipped=True, reason=message), indent=2, sort_keys=True))
        return 0
    print(f"WARN: {message}", file=sys.stderr)
    print(
        "      Not blocking -- this is a QA aid. Real enforcement needs a machine "
        "with lualatex, PyMuPDF, and NumPy installed.",
        file=sys.stderr,
    )
    return 0


def compile_fixture(workdir: Path) -> tuple[Path, str, int]:
    """Compile report.tex with lualatex; return the PDF, combined log, and exit status."""
    for src in (
        list(TEMPLATES.glob("*.cls"))
        + list(TEMPLATES.glob("*.def"))
        + list(TEMPLATES.glob("reportkit-*.tex"))
        + list(TEMPLATES.glob("*.sty"))
        + list((TEMPLATES / "themes").glob("*.sty"))
        + list((TEMPLATES / "publication_types").glob("*.sty"))
    ):
        shutil.copy(src, workdir / src.name)
    font_data = ROOT / "font_data"
    if font_data.is_dir():
        staged_fonts = workdir / "font_data"
        staged_fonts.mkdir()
        for source in sorted(font_data.glob("GoogleSans-*.ttf")):
            shutil.copy(source, staged_fonts / source.name)
    shutil.copy(EXAMPLE / "report.tex", workdir / "report.tex")
    shutil.copytree(EXAMPLE / "figures", workdir / "figures", dirs_exist_ok=True)

    log_chunks: list[str] = []
    returncode = 0
    for _ in range(2):  # two passes: cross-references/labels need a second pass to settle
        proc = run_limited(
            ["lualatex", "-file-line-error", "-interaction=nonstopmode", "-halt-on-error", "report.tex"],
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=120,
            memory_limit_mb=2048,
            env={
                **os.environ,
                # LuaLaTeX must read its installed article class and Unicode
                # data files; the fixture itself is checked in and shell
                # escape remains disabled by run_limited().
                "openin_any": "a",
                "openout_any": "p",
                "SOURCE_DATE_EPOCH": "1",
                "FORCE_SOURCE_DATE": "1",
                "TZ": "UTC",
            },
        )
        returncode = proc.returncode
        log_chunks.append(proc.stdout + "\n" + proc.stderr)
        if returncode:
            break
    pdf = workdir / "report.pdf"
    return pdf, "\n".join(log_chunks), returncode


def render_pages(pdf: Path, out_dir: Path, dpi: int) -> list[Path]:
    import pymupdf

    out_dir.mkdir(parents=True, exist_ok=True)
    matrix = pymupdf.Matrix(dpi / 72.0, dpi / 72.0)
    paths: list[Path] = []
    doc = pymupdf.open(pdf)
    for number, page in enumerate(doc, 1):
        out_path = out_dir / f"page-{number:02d}.png"
        page.get_pixmap(matrix=matrix, alpha=False).save(out_path)
        paths.append(out_path)
    doc.close()
    return paths


def compare_pages(actual_dir: Path, expected_dir: Path, *, threshold: float = 0.01) -> list[str]:
    """Pixel-diff every "page-NN.png" in actual_dir against expected_dir.

    A pure function of two directories of PNGs, deliberately independent of
    the lualatex compile / PDF render steps above so it can be exercised by
    tests/test_visual_qa_equity_research.py without a TeX install -- see
    that file for synthetic-PNG coverage of this function specifically.
    `threshold` is the fraction of differing pixels (0-1) tolerated before a
    page is reported as changed, to absorb harmless anti-aliasing /
    font-hinting drift between machines rather than flagging every pixel.
    """
    import numpy as np
    import pymupdf

    mismatches: list[str] = []
    actual_pages = sorted(p.name for p in actual_dir.glob("page-*.png"))
    expected_pages = sorted(p.name for p in expected_dir.glob("page-*.png"))
    if actual_pages != expected_pages:
        mismatches.append(f"page set differs: actual={actual_pages} expected={expected_pages}")
        return mismatches
    for name in actual_pages:
        a = pymupdf.Pixmap(str(actual_dir / name))
        b = pymupdf.Pixmap(str(expected_dir / name))
        if (a.width, a.height) != (b.width, b.height):
            mismatches.append(f"{name}: size differs {a.width}x{a.height} vs {b.width}x{b.height}")
            continue
        arr_a = np.frombuffer(a.samples, dtype=np.uint8).reshape(a.height, a.width, a.n)
        arr_b = np.frombuffer(b.samples, dtype=np.uint8).reshape(b.height, b.width, b.n)
        frac_diff = float(np.any(arr_a != arr_b, axis=-1).mean())
        if frac_diff > threshold:
            mismatches.append(f"{name}: {frac_diff:.2%} of pixels differ (threshold {threshold:.2%})")
    return mismatches


CHECKLIST = """
Spec section 25 manual-review checklist (not fully automatable by this script):
  [ ] page geometry matches the institutional-research theme's Letter/14mm geometry
  [ ] headline wrapping is clean on the front page (no orphaned single words)
  [ ] sidebar aligns with the main column baseline across all pages
  [ ] exhibit numbering and positioning follow reading order, with no overlap
  [ ] chart fonts read as the same family as body text (spec section 14)
  [ ] tables do not overflow the text block (Exhibit 4 / financial model / valuation)
  [ ] every exhibit and table has an aligned, muted source line
  [ ] no excessive blank pages or stranded section headings
  [ ] FAIL if chart y-tick font != chart x-tick font
  [ ] FAIL if requested Google Sans silently falls back (grep the lualatex
      log for "WARN institutional-research font" from the theme's own
      diagnostic, emitted by reportkit-theme-institutional-research.sty)
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--update-expected",
        action="store_true",
        help="Overwrite expected/ with this run's renders instead of comparing against it. "
        "Only after a human has reviewed the render against the checklist below.",
    )
    parser.add_argument("--dpi", type=int, default=150)
    parser.add_argument("--threshold", type=float, default=0.01, help="Fraction of differing pixels tolerated per page (default 1%%).")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if shutil.which("lualatex") is None:
        return _warn_exit0("lualatex not found on PATH -- skipping visual QA compile.", as_json=args.json)
    try:
        import numpy  # noqa: F401
        import pymupdf  # noqa: F401
    except ImportError as exc:
        return _warn_exit0(f"PyMuPDF and/or NumPy not importable ({exc}) -- skipping visual QA render/compare.", as_json=args.json)

    from reportkit import diagnostics

    baseline_path = EXPECTED / "baseline.json"
    if not baseline_path.is_file():
        diagnostic = make_diagnostic("toolchain_mismatch", f"missing visual baseline manifest: {baseline_path}", code="RK_BASELINE_MANIFEST_MISSING")
        if args.json:
            print(json.dumps(diagnostic_envelope([diagnostic], passed=False), indent=2, sort_keys=True))
        else:
            print(f"FAIL: {diagnostic['message']}", file=sys.stderr)
        return 5
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    toolchain = toolchain_context(ROOT)
    resolved = toolchain["resolved"]
    baseline_expected = baseline.get("expected_toolchain_fingerprint", baseline.get("toolchain_fingerprint"))
    baseline_resolved = baseline.get("resolved_toolchain_fingerprint", baseline.get("toolchain_fingerprint"))
    pinned_current = resolved["status"] == "pinned" and resolved.get("fingerprint") == toolchain["fingerprint"]
    baseline_matches = (
        baseline_expected == toolchain["fingerprint"]
        and baseline_resolved == resolved.get("fingerprint")
    )
    if not pinned_current or (not args.update_expected and not baseline_matches):
        diagnostic = make_diagnostic(
            "toolchain_mismatch",
            "visual comparison requires the exact toolchain recorded by expected/baseline.json",
            code="RK_VISUAL_TOOLCHAIN_MISMATCH",
            details={
                "baseline_expected": baseline_expected,
                "baseline_resolved": baseline_resolved,
                "expected": toolchain["fingerprint"],
                "resolved": resolved.get("fingerprint"),
            },
        )
        if args.json:
            print(json.dumps(diagnostic_envelope([diagnostic], passed=False), indent=2, sort_keys=True))
        else:
            print(f"FAIL: {diagnostic['message']}", file=sys.stderr)
        return 5
    if args.dpi != baseline.get("dpi") or args.threshold != baseline.get("pixel_difference_threshold"):
        diagnostic = make_diagnostic(
            "toolchain_mismatch", "visual DPI or threshold differs from the recorded baseline settings",
            code="RK_VISUAL_SETTINGS_MISMATCH", details={"baseline": baseline, "dpi": args.dpi, "threshold": args.threshold},
        )
        if args.json:
            print(json.dumps(diagnostic_envelope([diagnostic], passed=False), indent=2, sort_keys=True))
        else:
            print(f"FAIL: {diagnostic['message']}", file=sys.stderr)
        return 5

    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)
        try:
            pdf, log_text, compile_code = compile_fixture(workdir)
        except subprocess.TimeoutExpired:
            diagnostic = make_diagnostic(
                "compile_timeout", "equity-research visual fixture exceeded 120 seconds",
                code="RK_VISUAL_COMPILE_TIMEOUT",
            )
            if args.json:
                print(json.dumps(diagnostic_envelope([diagnostic], passed=False), indent=2, sort_keys=True))
            else:
                print(f"FAIL: {diagnostic['message']}", file=sys.stderr)
            return 4
        except (OSError, RuntimeError) as exc:
            diagnostic = make_diagnostic(
                "environment_error", f"visual fixture cannot enforce its build environment: {exc}",
                code="RK_VISUAL_ENVIRONMENT",
            )
            if args.json:
                print(json.dumps(diagnostic_envelope([diagnostic], passed=False), indent=2, sort_keys=True))
            else:
                print(f"FAIL: {diagnostic['message']}", file=sys.stderr)
            return 5
        if compile_code or not pdf.exists():
            memory_failure = compile_code < 0 or compile_code in {134, 137} or "memory" in log_text.lower()
            diagnostic = make_diagnostic(
                "compile_memory" if memory_failure else "compile_failure",
                f"lualatex visual fixture failed with status {compile_code}",
                code="RK_VISUAL_COMPILE_MEMORY" if memory_failure else "RK_VISUAL_COMPILE_FAILURE",
                details={"log_tail": log_text[-4000:]},
            )
            if args.json:
                print(json.dumps(diagnostic_envelope([diagnostic], passed=False), indent=2, sort_keys=True))
            else:
                print(f"FAIL: {diagnostic['message']}\n{log_text[-4000:]}", file=sys.stderr)
            return 4

        result = diagnostics.inspect_log(log_text)
        if not args.json:
            print(f"-- diagnostics: {result['counts']} --")
        blocking = [issue for issue in result["issues"] if issue["blocking"]]
        if blocking:
            if args.json:
                print(json.dumps(diagnostic_envelope(blocking, passed=False), indent=2, sort_keys=True))
            else:
                print("FAIL: blocking diagnostics found in the compile log:", file=sys.stderr)
                for issue in blocking:
                    location = f"{issue.get('file')}:{issue.get('line') or issue.get('log_line')}"
                    print(f"  {issue['type']} at {location}: {issue['message']}", file=sys.stderr)
            return 3

        rendered_dir = workdir / "rendered"
        pages = render_pages(pdf, rendered_dir, args.dpi)
        if not args.json:
            print(f"-- rendered {len(pages)} page(s) at {args.dpi} DPI --")

        if args.update_expected:
            EXPECTED.mkdir(parents=True, exist_ok=True)
            for old in EXPECTED.glob("page-*.png"):
                old.unlink()
            for page in pages:
                shutil.copy(page, EXPECTED / page.name)
            baseline["toolchain_fingerprint"] = toolchain["fingerprint"]
            baseline["expected_toolchain_fingerprint"] = toolchain["fingerprint"]
            baseline["resolved_toolchain_fingerprint"] = resolved["fingerprint"]
            baseline["pages"] = [page.name for page in pages]
            baseline_path.write_text(json.dumps(baseline, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            if args.json:
                print(json.dumps(diagnostic_envelope(
                    [], passed=True, updated=True, page_count=len(pages), baseline=str(EXPECTED),
                ), indent=2, sort_keys=True))
            else:
                print(f"PASS: wrote {len(pages)} baseline page(s) to {EXPECTED}")
                print(CHECKLIST)
            return 0

        if not any(EXPECTED.glob("page-*.png")):
            diagnostic = make_diagnostic(
                "visual_regression", f"{EXPECTED} has no baseline pages",
                code="RK_VISUAL_BASELINE_EMPTY",
            )
            if args.json:
                print(json.dumps(diagnostic_envelope([diagnostic], passed=False), indent=2, sort_keys=True))
            else:
                print(f"FAIL: {diagnostic['message']}", file=sys.stderr)
                print(CHECKLIST)
            return 3

        mismatches = compare_pages(rendered_dir, EXPECTED, threshold=args.threshold)
        if mismatches:
            records = [make_diagnostic(
                "visual_regression", mismatch, code="RK_VISUAL_REGRESSION",
                details={"baseline": str(EXPECTED), "dpi": args.dpi, "threshold": args.threshold},
            ) for mismatch in mismatches]
            if args.json:
                print(json.dumps(diagnostic_envelope(records, passed=False), indent=2, sort_keys=True))
            else:
                print("FAIL: rendered pages differ from expected/:", file=sys.stderr)
                for mismatch in mismatches:
                    print(f"  {mismatch}", file=sys.stderr)
            return 3

    if args.json:
        print(json.dumps(diagnostic_envelope(
            [], passed=True, page_count=len(pages), baseline=str(EXPECTED), dpi=args.dpi,
        ), indent=2, sort_keys=True))
    else:
        print("PASS: equity-research fixture compiled clean and matched expected/.")
        print(CHECKLIST)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
