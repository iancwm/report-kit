"""Compile small ReportKit figures and inspect their rendered PDF geometry."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

import pytest

# Import the scientific stack before PyMuPDF. Some Linux wheel combinations
# can disagree over the process-wide libstdc++ ABI; keeping this order makes a
# real incompatibility fail during collection instead of being hidden later
# by a test module's importorskip(). Missing optional packages remain optional
# for suites that do not use them.
try:
    import matplotlib  # noqa: F401
except ModuleNotFoundError as exc:
    if exc.name != "matplotlib":
        raise
try:
    import pandas  # noqa: F401
except ModuleNotFoundError as exc:
    if exc.name != "pandas":
        raise

import pymupdf

REPO = Path(__file__).resolve().parents[1]
TEMPLATES = REPO / "latex_templates"


@pytest.fixture(scope="session")
def latex_engine() -> str:
    engine = shutil.which("lualatex")
    if engine is None:
        pytest.skip("lualatex not on PATH")
    return engine


@pytest.fixture
def compile_doc(latex_engine: str, tmp_path: Path):
    def _compile(body: str, name: str = "doc", class_options: str = "") -> pymupdf.Document:
        tex = tmp_path / f"{name}.tex"
        documentclass = f"\\documentclass[{class_options}]{{reportkit}}" if class_options else "\\documentclass{reportkit}"
        font_setup = ""
        if "theme=institutional-research" in class_options:
            font_setup = f"\n\\setreportkitfontpath{{{REPO / 'font_data'}/}}"
        tex.write_text(documentclass + font_setup + "\n\\begin{document}\n" + body + "\n\\end{document}\n", encoding="utf-8")
        # LuaTeX exits before writing a log when it inherits an unavailable
        # locale such as en_US.UTF-8 from a GUI Git client. Keep the renderer
        # environment deterministic for tests.
        # Themes and publication types each live one directory deeper
        # (latex_templates/themes/, latex_templates/publication_types/);
        # include both explicitly so \documentclass{reportkit} can find a
        # non-default theme= or publication-type= file.
        env = dict(os.environ, LC_ALL="C", TEXINPUTS=f"{TEMPLATES}:{TEMPLATES / 'themes'}:{TEMPLATES / 'publication_types'}:")
        proc = subprocess.run(
            [latex_engine, "-file-line-error", "-interaction=nonstopmode", "-halt-on-error", tex.name],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            timeout=180,
        )
        pdf = tmp_path / f"{name}.pdf"
        if not pdf.exists():
            output = (proc.stdout + "\n" + proc.stderr)[-4000:]
            raise AssertionError(f"lualatex produced no PDF (exit {proc.returncode})\n{output}")
        return pymupdf.open(pdf)

    return _compile
