"""Static and contract regressions for the P3 algorithm-state extensions."""
from __future__ import annotations

from pathlib import Path

from reportkit.registry import generate_registry


REPO = Path(__file__).resolve().parents[1]
P3 = REPO / "latex_templates" / "reportkit-algorithm-p3.sty"


def test_algorithm_viz_loads_the_p3_extension_module() -> None:
    viz = (REPO / "latex_templates" / "reportkit-algorithm-viz.sty").read_text(encoding="utf-8")
    assert r"\RequirePackage{reportkit-algorithm-p3}" in viz


def test_p3_module_declares_all_figure_families_and_public_aliases() -> None:
    text = P3.read_text(encoding="utf-8")
    for environment in ("joinstate", "unionfindstate", "linkedliststate", "recursiontree"):
        assert rf"\NewDocumentEnvironment{{{environment}}}" in text
    for command in (
        "joininput", "hashbucket", "joinmatch", "joinunmatched", "joinoutput",
        "ufnode", "parent", "union", "findpath",
        "listnode", "nextlink", "head", "tail",
        "recursionnode", "recursionedge",
    ):
        assert rf"\NewDocumentCommand{{\{command}}}" in text
    for alias in (
        "hashindex", "joinpair", "joinresult", "findoperation",
        "linkednode", "listitem", "listlink", "nextpointer",
        "recursioncall", "recursionroot", "recursionlink", "recursionbranch",
    ):
        assert rf"\let\{alias}" in text


def test_p3_registry_has_four_figures_and_fifteen_commands() -> None:
    registry = generate_registry(REPO, strict=True)
    assert {
        name for name in registry["primitives"]["figure"]
        if name in {"joinstate", "unionfindstate", "linkedliststate", "recursiontree"}
    } == {"joinstate", "unionfindstate", "linkedliststate", "recursiontree"}
    assert {
        name for name in registry["primitives"]["command"]
        if registry["primitives"]["command"][name]["source"]["file"] == "latex_templates/reportkit-algorithm-p3.sty"
    } == {
        "joininput", "hashbucket", "joinmatch", "joinunmatched", "joinoutput",
        "ufnode", "parent", "union", "findpath",
        "listnode", "nextlink", "head", "tail",
        "recursionnode", "recursionedge",
    }

