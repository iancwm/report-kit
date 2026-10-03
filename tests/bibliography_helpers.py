"""Compile a ReportKit document through TeX -> bibtex -> TeX -> TeX."""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess

REPO = Path(__file__).resolve().parents[1]
TEMPLATES = REPO / "latex_templates"


@dataclass
class CompileResult:
    pdf: Path
    log: str
    text: str
    pages: list[str]
    returncode: int
    passes: int


def write_bibliography_config(directory: Path, *, stem: str, style: str, title: str, include_uncited: bool) -> None:
    (directory / "reportkit-bibliography-config.tex").write_text(
        "% Generated for tests.\n"
        f"\\renewcommand{{\\RKBibStyle}}{{{style}}}\n"
        f"\\renewcommand{{\\RKBibFile}}{{{stem}}}\n"
        f"\\renewcommand{{\\RKBibTitle}}{{{title}}}\n"
        + ("\\RKBibIncludeUncitedtrue\n" if include_uncited else "\\RKBibIncludeUncitedfalse\n"),
        encoding="utf-8",
    )


def compile_with_bibliography(
    tmp_path: Path, *, documentclass: str, body: str, bib: str | None, style: str = "numeric",
    title: str = "References", include_uncited: bool = False, preamble: str = "", engine: str = "pdflatex",
) -> CompileResult:
    import pymupdf

    tex = tmp_path / "doc.tex"
    tex.write_text(f"{documentclass}\n{preamble}\n\\begin{{document}}\n{body}\n\\end{{document}}\n", encoding="utf-8")
    if bib is not None:
        (tmp_path / "references.bib").write_text(bib, encoding="utf-8")
        write_bibliography_config(tmp_path, stem="references", style=style, title=title, include_uncited=include_uncited)
    env = dict(
        os.environ, LC_ALL="C",
        TEXINPUTS=f"{tmp_path}:{TEMPLATES}:{TEMPLATES / 'themes'}:{TEMPLATES / 'publication_types'}:",
    )
    command = [shutil.which(engine) or engine, "-file-line-error", "-interaction=nonstopmode", "-halt-on-error", "doc.tex"]
    log_parts: list[str] = []

    def tex_pass() -> int:
        proc = subprocess.run(command, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300)
        log_parts.append(proc.stdout)
        return proc.returncode

    passes = 1
    code = tex_pass()
    aux = tmp_path / "doc.aux"
    if code == 0 and bib is not None and aux.is_file() and "\\citation" in aux.read_text(encoding="utf-8", errors="replace"):
        bibtex = subprocess.run(["bibtex", "doc"], cwd=tmp_path, env=env, capture_output=True, text=True, timeout=120)
        log_parts.append(bibtex.stdout)
        code = bibtex.returncode if bibtex.returncode > 1 else 0  # bibtex exits 1 on warnings
        for _ in range(2):
            if code == 0:
                code = tex_pass()
                passes += 1
    elif code == 0:
        code = tex_pass()
        passes += 1
    pdf = tmp_path / "doc.pdf"
    pages: list[str] = []
    if pdf.is_file():
        with pymupdf.open(pdf) as document:
            pages = [page.get_text() for page in document]
    return CompileResult(pdf=pdf, log="\n".join(log_parts), text="\n".join(pages), pages=pages, returncode=code, passes=passes)
