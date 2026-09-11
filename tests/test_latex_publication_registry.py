from __future__ import annotations

import os
from pathlib import Path
import subprocess

import pytest

from reportkit.publications import render_latex_registry


REPO = Path(__file__).resolve().parents[1]


def test_generated_latex_registry_is_in_sync() -> None:
    path = REPO / "latex_templates" / "reportkit-publication-registry.def"
    assert path.read_text(encoding="utf-8") == render_latex_registry()


def test_generated_registry_contains_the_alias_and_supported_pairs() -> None:
    text = (REPO / "latex_templates" / "reportkit-publication-registry.def").read_text(encoding="utf-8")
    assert r"\csname RKThemeCanonical@technical\endcsname{default}" in text
    assert r"\DeclareOption{theme=technical}" in text
    assert r"\csname RKPublicationTheme@equity-research@institutional-research\endcsname" in text
    assert r"\csname RKPublicationTheme@technical-report@default\endcsname" in text


def test_latex_accepts_the_technical_compatibility_alias(compile_doc) -> None:
    doc = compile_doc(
        "Technical alias smoke test.",
        name="technical_alias_smoke",
        class_options="theme=technical,publication-type=technical-report",
    )
    assert doc.page_count >= 1


@pytest.mark.parametrize(
    ("options", "requested"),
    (
        ("theme=venture", "venture"),
        ("publication-type=venture-report", "venture-report"),
        ("theme=default,publication-type=equity-research", "default"),
    ),
)
def test_latex_rejects_unknown_or_unsupported_targets(
    latex_engine: str, tmp_path: Path, options: str, requested: str,
) -> None:
    source = tmp_path / "invalid.tex"
    source.write_text(
        f"\\documentclass[{options}]{{reportkit}}\n"
        "\\begin{document}This must not build.\\end{document}\n",
        encoding="utf-8",
    )
    env = dict(
        os.environ,
        LC_ALL="C",
        TEXINPUTS=f"{REPO / 'latex_templates'}:{REPO / 'latex_templates' / 'themes'}:{REPO / 'latex_templates' / 'publication_types'}:",
    )
    result = subprocess.run(
        [latex_engine, "-interaction=nonstopmode", "-halt-on-error", source.name],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "Class reportkit Error" in output
    assert requested in output
    assert not source.with_suffix(".pdf").exists()
