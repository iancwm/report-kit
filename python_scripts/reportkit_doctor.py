#!/usr/bin/env python3
"""ReportKit environment doctor.

Checks the capabilities needed for SOURCE BUILD and FULL BUILD without
requiring network access. Diagnostic mode reports gaps without failing; use
``--require full-build`` in CI when a missing dependency must block the build.
"""
from __future__ import annotations

import argparse
import importlib.util
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def check_import(name: str) -> tuple[bool, str]:
    spec = importlib.util.find_spec(name)
    if spec is None:
        return False, "not installed"
    try:
        module = __import__(name)
        version = getattr(module, "__version__", "installed")
        return True, str(version)
    except Exception as exc:  # pragma: no cover - diagnostic script
        return False, f"import failed: {exc}"


def check_executable(name: str) -> tuple[bool, str]:
    path = shutil.which(name)
    if not path:
        return False, "not found"
    try:
        proc = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=8)
        line = (proc.stdout or proc.stderr).splitlines()[0]
        return True, line.strip()
    except Exception:
        return True, path


def check_pymupdf() -> tuple[bool, str]:
    """Check the locked guide renderer environment before the host interpreter."""
    candidates = [
        (Path(sys.executable), "host Python"),
        (ROOT.parent / "data_engineering_guide" / "build" / ".venv" / "bin" / "python", "guide venv"),
    ]
    code = (
        "try:\n"
        " import pymupdf\n"
        " print(getattr(pymupdf, '__version__', getattr(pymupdf, 'VersionBind', 'installed')))\n"
        "except ImportError:\n"
        " import fitz\n"
        " print(getattr(fitz, 'VersionBind', 'installed'))\n"
    )
    for python, label in candidates:
        if not python.is_file():
            continue
        try:
            proc = subprocess.run([str(python), "-c", code], capture_output=True, text=True, timeout=8)
        except (OSError, subprocess.SubprocessError):
            continue
        if proc.returncode == 0 and proc.stdout.strip():
            return True, f"{proc.stdout.strip().splitlines()[0]} ({label})"
    return False, "not installed in host Python or guide venv"


def check_kpse(name: str) -> tuple[bool, str]:
    """Check a TeX file is findable on the current texmf tree via kpsewhich.

    pdflatex/lualatex being installed does not guarantee the fonts a class
    depends on are installed. reportkit.cls requires the Libertinus font
    packages (from texlive-fonts-extra on Debian/Ubuntu); without them,
    compilation fails on the first \\RequirePackage in the class, not on a
    missing binary, so this must be checked separately.
    """
    path = shutil.which("kpsewhich")
    if not path:
        return False, "kpsewhich not found"
    try:
        proc = subprocess.run([path, name], capture_output=True, text=True, timeout=8)
        found = proc.stdout.strip()
        return (True, found) if found else (False, "not found on texmf tree")
    except Exception as exc:  # pragma: no cover
        return False, str(exc)


def check_vector_export() -> tuple[bool, str]:
    try:
        sys.path.insert(0, str(ROOT))
        import reportkit_viz as rkv
        import pandas as pd

        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "doctor_plot"
            s = pd.Series([0.0, 0.1, 0.05], index=pd.date_range("2026-01-31", periods=3, freq="ME"))
            fig, _ = rkv.timeseries(s)
            rkv.save_figure(fig, out)
            pdf = out.with_suffix(".pdf")
            png = out.with_suffix(".png")
            if pdf.exists() and pdf.stat().st_size > 0 and png.exists() and png.stat().st_size > 0:
                return True, "PDF + PNG export works"
            return False, "export files missing"
    except Exception as exc:  # pragma: no cover
        return False, str(exc)


def print_check(label: str, result: tuple[bool, str]) -> bool:
    ok, detail = result
    status = "OK" if ok else "--"
    print(f"[{status}] {label}: {detail}")
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require", choices=("full-build",), help="fail unless the requested build mode is available")
    args = parser.parse_args()

    print("ReportKit environment doctor")
    print(f"[OK] Python: {sys.version.split()[0]}")
    py_ok = True
    for pkg in ("matplotlib", "numpy", "pandas"):
        py_ok &= print_check(pkg, check_import(pkg))
    viz_ok = print_check("ReportKit vector export", check_vector_export()) if py_ok else False

    print()
    pdflatex_ok = print_check("pdflatex", check_executable("pdflatex"))
    lualatex_ok = print_check("lualatex", check_executable("lualatex"))
    bibtex_ok = print_check("bibtex", check_executable("bibtex"))
    biber_ok = print_check("biber", check_executable("biber"))

    print()
    fonts_ok = print_check("libertinus.sty", check_kpse("libertinus.sty"))
    fonts_ok &= print_check("libertinust1math.sty", check_kpse("libertinust1math.sty"))

    print()
    pandoc_ok = print_check("pandoc", check_executable("pandoc"))
    pymupdf_ok = print_check("PyMuPDF (guide renderer)", check_pymupdf())

    tex_ok = pdflatex_ok or lualatex_ok
    full_ok = py_ok and viz_ok and tex_ok and fonts_ok and pandoc_ok and pymupdf_ok
    print()
    if full_ok:
        print("MODE: FULL BUILD")
        if not (bibtex_ok or biber_ok):
            print("NOTE: bibliography tool not found; reports without external bibliography can still compile.")
    elif py_ok and viz_ok and tex_ok and not fonts_ok:
        print("MODE: SOURCE BUILD + FIGURES")
        print("TeX is installed but the Libertinus fonts reportkit.cls requires are missing.")
        print("On Debian/Ubuntu: apt-get install -y texlive-fonts-extra")
    elif py_ok and viz_ok:
        print("MODE: SOURCE BUILD + FIGURES")
        print("TeX compilation is unavailable, but ReportKit analytical figures can be generated.")
    else:
        print("MODE: SOURCE BUILD")
        print("Generate a portable ReportKit source bundle; do not promise compiled output.")
    if args.require and not full_ok:
        print(f"REQUIREMENT FAILED: {args.require}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
