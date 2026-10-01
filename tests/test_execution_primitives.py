"""Execution surfaces (terminalblock, diffblock and their line macros).

Static contract checks always run. Compile tests need pdfLaTeX and skip
cleanly without it; they use whatever pdfLaTeX is installed rather than the
pinned image, so a pass here is not the pinned-toolchain acceptance gate.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess

import pytest

from reportkit.registry import generate_registry

REPO = Path(__file__).resolve().parents[1]
TEMPLATES = REPO / "latex_templates"
EXECUTION = TEMPLATES / "reportkit-execution.sty"
THEMES = ("operator", "default")

requires_pdflatex = pytest.mark.skipif(
    shutil.which("pdflatex") is None,
    reason="the operator theme is pdfLaTeX-only and pdflatex is not on PATH",
)


def _compile(tmp_path: Path, body: str, *, theme: str = "operator", name: str = "doc") -> tuple[subprocess.CompletedProcess, str]:
    tex = tmp_path / f"{name}.tex"
    tex.write_text(
        f"\\documentclass[publication-type=technical-report,theme={theme}]{{reportkit}}\n"
        f"\\begin{{document}}\n{body}\n\\end{{document}}\n",
        encoding="utf-8",
    )
    env = dict(
        os.environ,
        LC_ALL="C",
        TEXINPUTS=f"{TEMPLATES}:{TEMPLATES / 'themes'}:{TEMPLATES / 'publication_types'}:",
    )
    proc = subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "-file-line-error", tex.name],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=240,
    )
    log_path = tex.with_suffix(".log")
    log = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
    return proc, log


def _errors(log: str) -> list[str]:
    return re.findall(r"^(?:!|\S+\.tex:\d+:).*$", log, re.M)


# ------------------------------------------------------------------ contract


def test_execution_contract_records_exist() -> None:
    records = generate_registry()["primitives"]
    commands, compositions = records["command"], records["composition"]
    assert {"terminalblock", "diffblock"} <= set(compositions)
    for name, environment in {
        "termline": "terminalblock", "termprompt": "terminalblock", "termcomment": "terminalblock",
        "diffadd": "diffblock", "diffdel": "diffblock", "diffctx": "diffblock", "diffhunk": "diffblock",
    }.items():
        constraints = commands[name]["constraints"]
        assert {"code": "environment", "value": environment} == {
            k: v for k, v in next(c for c in constraints if c["code"] == "environment").items() if k != "description"
        }


def test_execution_module_does_not_branch_on_theme_name() -> None:
    source = EXECUTION.read_text(encoding="utf-8")
    assert "rk@theme" not in source
    assert "operator" not in source.lower()


def test_execution_module_reads_only_terminal_and_diff_tokens() -> None:
    tokens = set(re.findall(r"\\RKTok[A-Za-z]+", EXECUTION.read_text(encoding="utf-8")))
    assert tokens
    stray = sorted(t for t in tokens if not t.startswith(("\\RKTokTerminal", "\\RKTokDiff", "\\RKTokAssert")))
    assert stray == []


def test_terminal_body_text_color_is_an_explicit_token() -> None:
    """Spec section 8 item 1: the body must never inherit black."""
    source = EXECUTION.read_text(encoding="utf-8")
    assert "colupper=\\RKTokTerminalText" in source.replace(" ", "")


# ------------------------------------------------------------------ positive


SPECIAL = r"\$ \_ \% \# \& \textbackslash{} \{ \} \textasciitilde{} \textasciicircum{}"


def _blocks(special: str = SPECIAL) -> str:
    return (
        "\\begin{terminalblock}[Metered credits vs direct API]\n"
        "\\termcomment{invoice = F + max(0, N*c - A)}\n"
        "\\termprompt{atlas cost --attempts 80}\n"
        "\\termline{Total: \\$212.40 (credit cap reached at attempt 64)}\n"
        "\\termline{}\n"
        f"\\termline{{~~{special}}}\n"
        "\\end{terminalblock}\n\n"
        "\\begin{diffblock}[src/auth/session.ts]\n"
        "\\diffhunk{@@ -12,3 +12,3 @@}\n"
        "\\diffdel{const token = req.headers['x-token'];}\n"
        "\\diffadd{const token = verifyJWT(req.headers.authorization);}\n"
        "\\diffctx{if (!token) return deny(res);}\n"
        f"\\diffctx{{{special}}}\n"
        "\\end{diffblock}\n"
    )


@requires_pdflatex
@pytest.mark.parametrize("theme", THEMES)
def test_blocks_compile_with_every_escaped_special_character(tmp_path: Path, theme: str) -> None:
    proc, log = _compile(tmp_path, _blocks(), theme=theme)
    assert proc.returncode == 0, _errors(log)
    assert "Overfull \\hbox" not in log
    assert (tmp_path / "doc.pdf").exists()


@requires_pdflatex
def test_long_line_wraps_without_overfull(tmp_path: Path) -> None:
    long_line = " ".join(["wordy"] * 60)
    body = (
        f"\\begin{{terminalblock}}\n\\termline{{{long_line}}}\n\\end{{terminalblock}}\n"
        f"\\begin{{diffblock}}\n\\diffadd{{{long_line}}}\n\\end{{diffblock}}\n"
    )
    proc, log = _compile(tmp_path, body)
    assert proc.returncode == 0, _errors(log)
    assert "Overfull \\hbox" not in log


@requires_pdflatex
def test_ac11_long_diff_breaks_across_pages_without_overflow(tmp_path: Path) -> None:
    pymupdf = pytest.importorskip("pymupdf")
    lines = []
    for n in range(120):
        macro = ("diffadd", "diffdel", "diffctx")[n % 3]
        lines.append(f"\\{macro}{{line {n:03d} of a deliberately long fictional change}}")
    body = "\\begin{diffblock}[long.py]\n" + "\n".join(lines) + "\n\\end{diffblock}\n"
    proc, log = _compile(tmp_path, body)
    assert proc.returncode == 0, _errors(log)
    assert "Overfull" not in log
    with pymupdf.open(tmp_path / "doc.pdf") as document:
        assert document.page_count >= 2
        text = "\n".join(page.get_text() for page in document)
        for n in (0, 59, 119):
            assert f"line {n:03d}" in text
        for page in document:
            width = page.rect.width
            for block in page.get_text("blocks"):
                assert block[0] >= 0 and block[2] <= width


@requires_pdflatex
def test_ac4_terminal_text_is_light_on_dark_surface(tmp_path: Path) -> None:
    pymupdf = pytest.importorskip("pymupdf")
    np = pytest.importorskip("numpy")
    body = (
        "\\begin{terminalblock}\n"
        + "\n".join("\\termline{Total: output line %d}" % n for n in range(12))
        + "\n\\end{terminalblock}\n"
    )
    proc, log = _compile(tmp_path, body)
    assert proc.returncode == 0, _errors(log)
    with pymupdf.open(tmp_path / "doc.pdf") as document:
        page = document[0]
        match = page.search_for("Total: output line 3")
        assert match, "terminal text not found in the rendered page"
        zoom = 140 / 72
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
        pixels = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(pixmap.height, pixmap.width, 3)
        rect = match[0]
        crop = pixels[int(rect.y0 * zoom): int(rect.y1 * zoom) + 1, int(rect.x0 * zoom): int(rect.x1 * zoom) + 1]
    luminance = crop.astype(float).mean(axis=2) / 255.0
    assert float(np.median(luminance)) < 0.25, "terminal surface is not dark"
    assert int((luminance > 0.8).sum()) >= 10, "no light glyph pixels on the terminal surface"


# ------------------------------------------------------------ misuse (loud)


@requires_pdflatex
@pytest.mark.parametrize(
    ("body", "diagnostic"),
    [
        ("\\termline{x}", "\\termline must be used inside terminalblock"),
        ("\\termprompt{x}", "\\termprompt must be used inside terminalblock"),
        ("\\termcomment{x}", "\\termcomment must be used inside terminalblock"),
        ("\\diffadd{x}", "\\diffadd must be used inside diffblock"),
        ("\\diffdel{x}", "\\diffdel must be used inside diffblock"),
        ("\\diffctx{x}", "\\diffctx must be used inside diffblock"),
        ("\\diffhunk{x}", "\\diffhunk must be used inside diffblock"),
        (
            "\\begin{diffblock}\\termline{x}\\end{diffblock}",
            "\\termline must be used inside terminalblock",
        ),
        (
            "\\begin{terminalblock}\\diffadd{x}\\end{terminalblock}",
            "\\diffadd must be used inside diffblock",
        ),
    ],
)
def test_line_macro_outside_its_block_fails_naming_the_environment(
    tmp_path: Path, body: str, diagnostic: str
) -> None:
    proc, log = _compile(tmp_path, body)
    flat = log.replace("\n", "")
    assert "Package reportkit-execution Error" in flat
    assert diagnostic.replace(" ", "") in flat.replace(" ", "")
    assert proc.returncode != 0
