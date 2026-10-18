"""Operator theme: registration, engine guard, palette parity and contract surface.

Registry and parity checks are pure Python. Compile checks need pdfLaTeX (or
LuaLaTeX for the negative engine-guard test) and skip cleanly without them.
They exercise the installed engine, not the pinned image, and say nothing
about visual quality; that is the Wave 3 review.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess

import pytest

from reportkit.publications import (
    PUBLICATION_TYPES,
    THEMES,
    PublicationRegistryError,
    resolve_build_target,
)
from reportkit.themes import get_theme

REPO = Path(__file__).resolve().parents[1]
TEMPLATES = REPO / "latex_templates"
THEME_STY = TEMPLATES / "themes" / "reportkit-theme-operator.sty"
ADAPTER_STY = TEMPLATES / "themes" / "reportkit-theme-operator-paged.sty"

requires_pdflatex = pytest.mark.skipif(shutil.which("pdflatex") is None, reason="pdflatex is not on PATH")
requires_lualatex = pytest.mark.skipif(
    shutil.which("lualatex") is None, reason="lualatex is not on PATH; cannot test the engine guard"
)


def _sty_palette() -> dict[str, str]:
    text = THEME_STY.read_text(encoding="utf-8")
    return {
        name: value.upper()
        for name, value in re.findall(r"\\definecolor\{(\w+)\}\{HTML\}\{([0-9A-Fa-f]{6})\}", text)
    }


def _compile(tmp_path: Path, engine: str, body: str = "Hello") -> tuple[subprocess.CompletedProcess, str]:
    tex = tmp_path / "doc.tex"
    tex.write_text(
        "\\documentclass[publication-type=technical-report,theme=operator]{reportkit}\n"
        f"\\begin{{document}}\n{body}\n\\end{{document}}\n",
        encoding="utf-8",
    )
    env = dict(
        os.environ,
        LC_ALL="C",
        TEXINPUTS=f"{TEMPLATES}:{TEMPLATES / 'themes'}:{TEMPLATES / 'publication_types'}:",
    )
    proc = subprocess.run(
        [engine, "-interaction=nonstopmode", "-file-line-error", tex.name],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=240,
    )
    log_path = tex.with_suffix(".log")
    return proc, (log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else "")


# ------------------------------------------------------------- registration


def test_operator_is_registered_experimental_paged_pdflatex() -> None:
    record = THEMES["operator"]
    assert record["renderers"] == ["paged"]
    assert record["required_engine"] == "pdflatex"
    assert record["stability"] == "experimental"
    assert record["common_package"] == "reportkit-theme-operator"
    assert record["renderer_adapters"] == {"paged": "reportkit-theme-operator-paged"}


def test_operator_pairs_only_with_technical_report() -> None:
    paired = [name for name, record in PUBLICATION_TYPES.items() if "operator" in record["themes"]]
    assert paired == ["technical-report"]


def test_resolve_build_target_selects_pdflatex() -> None:
    target = resolve_build_target("technical-report", "operator")
    assert (target.theme, target.engine, target.renderer) == ("operator", "pdflatex", "paged")
    assert target.renderer_adapter == "reportkit-theme-operator-paged"


def test_resolve_build_target_rejects_lualatex_with_actionable_message() -> None:
    with pytest.raises(PublicationRegistryError, match=r"requires engine 'pdflatex'.*--engine pdflatex"):
        resolve_build_target("technical-report", "operator", engine="lualatex")


def test_resolve_build_target_rejects_unpaired_publication_type() -> None:
    with pytest.raises(PublicationRegistryError, match="does not support publication type"):
        resolve_build_target("equity-research", "operator")


def test_theme_files_exist_and_are_loadable_by_name() -> None:
    assert THEME_STY.is_file() and ADAPTER_STY.is_file()
    assert get_theme("operator").name == "operator"


# --------------------------------------------------------------- parity


def test_python_palette_matches_sty_hex_values() -> None:
    sty = _sty_palette()
    python = get_theme("operator").latex_colors
    assert python
    for name, value in python.items():
        assert name in sty, f"{name} is declared in Python but not defined in the .sty"
        assert sty[name] == value.lstrip("#").upper(), f"{name}: .sty {sty[name]} != Python {value}"


def test_python_surface_matches_sty_surface() -> None:
    theme = get_theme("operator")
    assert theme.surface.lstrip("#").upper() == _sty_palette()["Surface"]


def test_no_public_color_name_uses_reserved_rk_prefix() -> None:
    assert [name for name in _sty_palette() if name.lower().startswith("rk")] == []


def test_theme_files_do_not_load_packages_with_options_a_second_time() -> None:
    """Spec section 8 item 4: theme files configure, they never reload."""
    for path in (THEME_STY, ADAPTER_STY):
        code = "\n".join(re.sub(r"(?<!\\)%.*$", "", line) for line in path.read_text(encoding="utf-8").splitlines())
        reloaded = re.findall(r"\\RequirePackage\[[^\]]+\]\{(geometry|caption|titlesec|fancyhdr)\}", code)
        assert reloaded == [], f"{path.name} reloads {reloaded} with options"


def test_chart_tokens_are_part_of_the_theme() -> None:
    charts = get_theme("operator").charts
    assert charts.hatches and charts.dashes


# ----------------------------------------------------------------- compile


@requires_pdflatex
def test_operator_minimal_document_compiles_under_pdflatex(tmp_path: Path) -> None:
    proc, log = _compile(tmp_path, "pdflatex", "\\section{Heading}\nBody text.")
    assert proc.returncode == 0, "\n".join(re.findall(r"^(?:!|\S+\.tex:\d+:).*$", log, re.M))
    assert "Overfull \\hbox" not in log


@requires_pdflatex
def test_operator_minimal_document_has_no_headheight_warning(tmp_path: Path) -> None:
    _, log = _compile(tmp_path, "pdflatex", "\\section{Heading}\nBody text.")
    assert "\\headheight is too small" not in log.replace("\n", " ")


@requires_lualatex
def test_engine_guard_fails_under_lualatex_with_clear_message(tmp_path: Path) -> None:
    proc, log = _compile(tmp_path, "lualatex")
    assert proc.returncode != 0
    assert "requires pdfLaTeX" in log.replace("\n", "")
    assert not (tmp_path / "doc.pdf").exists()
