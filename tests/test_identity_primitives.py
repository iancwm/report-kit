"""Identity primitives (productchip, statusdot, capabilitygrid): contracts and AC10.

Static contract checks always run. Compile tests need pdfLaTeX (the operator
theme is pdfTeX-only) and skip cleanly where it is not on PATH. Compiles use
whatever pdfLaTeX is installed, not the pinned image, so they establish
behaviour only; the pinned-toolchain gate is run separately.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

import pytest

from reportkit.registry import generate_registry

REPO = Path(__file__).resolve().parents[1]
TEMPLATES = REPO / "latex_templates"
IDENTITY = TEMPLATES / "reportkit-identity.sty"
THEMES_WITH_TOKENS = ("operator", "default")

requires_pdflatex = pytest.mark.skipif(
    shutil.which("pdflatex") is None,
    reason="the operator theme is pdfLaTeX-only and pdflatex is not on PATH",
)

IDENTITY_PRIMITIVES = {
    "productchip", "productavatar", "pricepill", "statusdot",
    "capabilitygrid", "capabilityrow", "capdocumented", "capunestablished",
}


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


def _grid(rows: str, columns: str = "A,B,C", options: str = "") -> str:
    return (
        f"\\begin{{capabilitygrid}}[{options}]{{{columns}}}\n{rows}\n\\end{{capabilitygrid}}"
    )


# ------------------------------------------------------------------ contract


def test_identity_contract_records_exist_with_final_signatures() -> None:
    records = {**generate_registry()["primitives"]["command"], **generate_registry()["primitives"]["composition"]}
    assert IDENTITY_PRIMITIVES <= set(records)
    assert [a["name"] for a in records["productchip"]["arguments"]] == ["initial", "name", "tag"]
    assert [a["name"] for a in records["pricepill"]["arguments"]] == ["price", "plan"]
    status = records["statusdot"]
    enum = [c for c in status["constraints"] if c["code"] == "enum"][0]
    assert enum["values"] == ["verified", "flag", "accent", "neutral"]
    assert any(c["code"] == "prose_only" for c in records["productavatar"]["constraints"])


def test_identity_module_does_not_branch_on_theme_name() -> None:
    source = IDENTITY.read_text(encoding="utf-8")
    assert "operator" not in source.lower().replace("operators", "")
    assert "rk@theme" not in source


def test_identity_module_reads_only_identity_or_capability_tokens() -> None:
    import re

    tokens = set(re.findall(r"\\RKTok[A-Za-z]+", IDENTITY.read_text(encoding="utf-8")))
    assert tokens
    allowed = ("\\RKTokIdentity", "\\RKTokCapability")
    stray = sorted(t for t in tokens if not t.startswith(allowed))
    assert stray == []


# ----------------------------------------------------------------- positive


@requires_pdflatex
@pytest.mark.xfail(
    strict=True,
    reason=(
        "discrepancy: reportkit-identity.sty writes multi-word TikZ keys ('rounded corners', "
        "'inner sep', 'minimum size', 'line width') inside \\ExplSyntaxOn, where spaces are "
        "ignored, so \\pricepill, \\statusdot and \\productavatar raise pgfkeys errors "
        "(/tikz/roundedcorners, /tikz/innersep, /tikz/minimumsize) under every theme"
    ),
)
@pytest.mark.parametrize("theme", THEMES_WITH_TOKENS)
def test_identity_primitives_compile_under_theme(tmp_path: Path, theme: str) -> None:
    body = (
        "\\productchip{A}{Atlas CLI}{first-party} \\pricepill{\\$12}{Team} "
        "\\statusdot{verified}\\statusdot{flag}\\statusdot{accent}\\statusdot{neutral}\n\n"
        "\\productavatar{A}{Atlas CLI}{first-party}\n\n"
        + _grid("\\capabilityrow[first-party]{Atlas}{D-D}\n\\capabilityrow{Beacon}{--D}")
    )
    proc, log = _compile(tmp_path, body, theme=theme)
    assert proc.returncode == 0, log[-3000:]
    assert (tmp_path / "doc.pdf").exists()
    assert "Overfull \\hbox" not in log


@requires_pdflatex
def test_twelve_column_grid_fits_linewidth_without_overfull(tmp_path: Path) -> None:
    columns = ",".join(f"C{i}" for i in range(1, 13))
    rows = "\n".join(
        f"\\capabilityrow{{Product {n}}}{{{'D--' * 4}}}" for n in range(1, 4)
    )
    proc, log = _compile(tmp_path, _grid(rows, columns))
    assert proc.returncode == 0, log[-3000:]
    assert "Overfull \\hbox" not in log


@requires_pdflatex
@pytest.mark.xfail(
    strict=True,
    reason=(
        "discrepancy: reportkit-identity.sty writes 'line width=' inside \\ExplSyntaxOn, "
        "where the space is dropped, so \\capunestablished (any U cell) raises "
        "'pgfkeys Error: I do not know the key /tikz/linewidth' under every theme"
    ),
)
@pytest.mark.parametrize("theme", THEMES_WITH_TOKENS)
def test_unestablished_capability_glyph_compiles_cleanly(tmp_path: Path, theme: str) -> None:
    proc, log = _compile(tmp_path, "\\capunestablished\\ " + _grid("\\capabilityrow{A}{UUU}"), theme=theme)
    assert proc.returncode == 0, log[-1500:]


@requires_pdflatex
def test_productchip_is_safe_inside_a_table_cell(tmp_path: Path) -> None:
    body = "\\begin{tabular}{ll}\\productchip{A}{Atlas}{tag} & x\\\\\\end{tabular}"
    proc, log = _compile(tmp_path, body)
    assert proc.returncode == 0, log[-3000:]


# ------------------------------------------------------- AC10: loud misuse


MISUSE = [
    pytest.param(
        _grid("\\capabilityrow{Atlas}{D-}"),
        "has 2 cells, but the grid has 3 columns",
        id="row-too-short",
    ),
    pytest.param(
        _grid("\\capabilityrow{Atlas}{D-DD}"),
        "has 4 cells, but the grid has 3 columns",
        id="row-too-long",
    ),
    pytest.param(
        _grid("\\capabilityrow{Atlas}{DQD}"),
        "Invalid capability marker",
        id="bad-marker",
    ),
    pytest.param("\\statusdot{purple}", "Unknown status state 'purple'", id="unknown-state"),
    pytest.param(
        "\\begin{tabular}{l}\\productavatar{A}{Atlas}{tag}\\\\\\end{tabular}",
        "cannot be used inside alignment environment",
        id="avatar-in-table",
    ),
    pytest.param(
        _grid("\\capabilityrow{Atlas}{D}", "A,,B"),
        "empty column heading",
        id="empty-heading",
    ),
]


@requires_pdflatex
@pytest.mark.parametrize(("body", "diagnostic"), MISUSE)
def test_misuse_fails_with_named_package_error(tmp_path: Path, body: str, diagnostic: str) -> None:
    proc, log = _compile(tmp_path, body)
    flat = log.replace("\n", "")
    assert "Package reportkit-identity Error" in flat, flat[-2000:]
    assert diagnostic.replace(" ", "") in flat.replace(" ", "")
    # nonstopmode finishes the run, but the engine must report failure.
    assert proc.returncode != 0
