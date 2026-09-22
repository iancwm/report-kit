"""Acceptance checks for the native presentation density fixture."""
from __future__ import annotations

from pathlib import Path
import re

REPO = Path(__file__).resolve().parents[1]
FIXTURE = REPO / "latex_templates" / "examples" / "executive-presentation-density"


def test_density_fixture_declares_native_presentation_target() -> None:
    publication = (FIXTURE / "publication.yaml").read_text(encoding="utf-8")
    assert "engine: lualatex" in publication
    assert "theme: executive" in publication
    assert "publication_type: presentation" in publication


def test_density_fixture_covers_the_required_slide_inventory() -> None:
    report = (FIXTURE / "report.tex").read_text(encoding="utf-8")
    assert len(re.findall(r"\\begin\{frame\}(?:\[plain\])?", report)) == 9
    assert report.count(r"\begin{assertionslide}") == 6
    assert r"\begin{messageslide}" in report
    assert r"\begin{referenceslide}" in report
    assert r"\begin{comparison}" in report
    assert r"\begin{threepart}" in report
    assert "fig-density-flow.tex" in report


def test_density_fixture_uses_semantic_roles_not_local_font_hacks() -> None:
    report = (FIXTURE / "report.tex").read_text(encoding="utf-8")
    manuscript = (FIXTURE / "manuscript" / "01-density.md").read_text(encoding="utf-8")
    assert r"\fontsize" not in report
    assert r"\tiny" not in report
    assert "local font-size hacks" in report
    assert manuscript.count("~~~reportkit") == 8
    assert "messageslide" in manuscript
    assert "referenceslide" in manuscript
