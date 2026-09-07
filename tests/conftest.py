"""Compile small ReportKit figures and inspect their rendered PDF geometry."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

import pytest
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
    def _compile(body: str, name: str = "doc") -> pymupdf.Document:
        tex = tmp_path / f"{name}.tex"
        tex.write_text("\\documentclass{reportkit}\n\\begin{document}\n" + body + "\n\\end{document}\n", encoding="utf-8")
        # LuaTeX exits before writing a log when it inherits an unavailable
        # locale such as en_US.UTF-8 from a GUI Git client. Keep the renderer
        # environment deterministic for tests.
        env = dict(os.environ, LC_ALL="C", TEXINPUTS=f"{TEMPLATES}:")
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
