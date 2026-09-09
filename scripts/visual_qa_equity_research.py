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


def _warn_exit0(message: str) -> int:
    print(f"WARN: {message}", file=sys.stderr)
    print(
        "      Not blocking -- this is a QA aid. Real enforcement needs a machine "
        "with lualatex, PyMuPDF, and NumPy installed.",
        file=sys.stderr,
    )
    return 0


def compile_fixture(workdir: Path) -> tuple[Path, str]:
    """Compile report.tex with lualatex into workdir; return (pdf_path, combined stdout+stderr log)."""
    for src in (
        list(TEMPLATES.glob("*.cls"))
        + list(TEMPLATES.glob("*.sty"))
        + list((TEMPLATES / "themes").glob("*.sty"))
        + list((TEMPLATES / "publication_types").glob("*.sty"))
    ):
        shutil.copy(src, workdir / src.name)
    shutil.copy(EXAMPLE / "report.tex", workdir / "report.tex")
    shutil.copytree(EXAMPLE / "figures", workdir / "figures", dirs_exist_ok=True)

    log_text = ""
    for _ in range(2):  # two passes: cross-references/labels need a second pass to settle
        proc = subprocess.run(
            ["lualatex", "-file-line-error", "-interaction=nonstopmode", "-halt-on-error", "report.tex"],
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=180,
        )
        log_text = proc.stdout + "\n" + proc.stderr
    pdf = workdir / "report.pdf"
    return pdf, log_text


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
    args = parser.parse_args()

    if shutil.which("lualatex") is None:
        return _warn_exit0("lualatex not found on PATH -- skipping visual QA compile.")
    try:
        import numpy  # noqa: F401
        import pymupdf  # noqa: F401
    except ImportError as exc:
        return _warn_exit0(f"PyMuPDF and/or NumPy not importable ({exc}) -- skipping visual QA render/compare.")

    from reportkit import diagnostics

    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)
        pdf, log_text = compile_fixture(workdir)
        if not pdf.exists():
            print("FAIL: lualatex produced no PDF. Last 4000 characters of log:", file=sys.stderr)
            print(log_text[-4000:], file=sys.stderr)
            return 1

        result = diagnostics.inspect_log(log_text)
        print(f"-- diagnostics: {result['counts']} --")
        blocking = [issue for issue in result["issues"] if issue["blocking"]]
        if blocking:
            print("FAIL: blocking diagnostics found in the compile log:", file=sys.stderr)
            for issue in blocking:
                location = f"{issue.get('file')}:{issue.get('line', issue['log_line'])}"
                print(f"  {issue['type']} at {location}: {issue['message']}", file=sys.stderr)
            return 1

        rendered_dir = workdir / "rendered"
        pages = render_pages(pdf, rendered_dir, args.dpi)
        print(f"-- rendered {len(pages)} page(s) at {args.dpi} DPI --")

        if args.update_expected:
            EXPECTED.mkdir(parents=True, exist_ok=True)
            for old in EXPECTED.glob("page-*.png"):
                old.unlink()
            for page in pages:
                shutil.copy(page, EXPECTED / page.name)
            print(f"PASS: wrote {len(pages)} baseline page(s) to {EXPECTED}")
            print(CHECKLIST)
            return 0

        if not any(EXPECTED.glob("page-*.png")):
            print(
                f"WARN: {EXPECTED} has no baseline pages yet -- review this run's render "
                "against the checklist below, then re-run with --update-expected.",
                file=sys.stderr,
            )
            print(CHECKLIST)
            return 0

        mismatches = compare_pages(rendered_dir, EXPECTED, threshold=args.threshold)
        if mismatches:
            print("FAIL: rendered pages differ from expected/:", file=sys.stderr)
            for mismatch in mismatches:
                print(f"  {mismatch}", file=sys.stderr)
            return 1

    print("PASS: equity-research fixture compiled clean and matched expected/.")
    print(CHECKLIST)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
