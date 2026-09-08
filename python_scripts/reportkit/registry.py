"""Machine-readable inventory of ReportKit's public visual primitives."""
from __future__ import annotations

import ast
from pathlib import Path
import re
from typing import Any

CALLOUT_ALIASES = {"evidence": "evidencenote", "limitation": "limitationnote", "tip": "tipnote"}
NON_FIGURE_ENVIRONMENTS = {"diagram", "RKShortListing", "outputblock"}
PUBLIC_CHART_NAMES = {
    "timeseries", "bar_chart", "distribution", "scatter_plot", "heatmap", "drawdown_chart",
    "waterfall_chart", "treemap_chart", "tornado_chart", "bubble_matrix", "timeline_chart",
}
COMMANDS = {
    "doctor": "reportkit doctor",
    "context": "reportkit context",
    "check": "reportkit check",
    "build": "reportkit build",
    "diagnose": "reportkit diagnose",
    "inspect": "reportkit inspect",
    "package": "reportkit package",
    "analyse-history": "reportkit analyse-history",
}


def _environments(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    return set(re.findall(r"\\NewDocumentEnvironment\{([^}]+)\}", text))


def _figure_environments(template_root: Path) -> list[str]:
    found: set[str] = set()
    for path in template_root.glob("reportkit*.sty"):
        if path.name == "reportkit-boxes.sty":
            continue
        found.update(_environments(path))
    return sorted(found - NON_FIGURE_ENVIRONMENTS)


def _callouts(template_root: Path) -> dict[str, Any]:
    boxes = template_root / "reportkit-boxes.sty"
    found = _environments(boxes)
    primary = sorted(found - set(CALLOUT_ALIASES))
    return {
        "public": primary,
        "aliases": {name: target for name, target in CALLOUT_ALIASES.items() if name in found},
    }


def _charts(python_path: Path) -> list[str]:
    tree = ast.parse(python_path.read_text(encoding="utf-8"))
    return sorted(
        node.name for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in PUBLIC_CHART_NAMES
    )


def skill_inventory(skill_path: Path) -> dict[str, set[str]]:
    text = skill_path.read_text(encoding="utf-8")
    figures: set[str] = set()
    for line in text.splitlines():
        if "|" in line and "Use" not in line and "---" not in line:
            cells = [cell.strip() for cell in line.split("|")]
            if len(cells) >= 3:
                figures.update(name for name in re.findall(r"`([^`]+)`", cells[2]) if name != "reportkit_viz.py")
    callout_match = re.search(r"Use semantic callouts only when their meaning matters:\s*([^\.]+)", text)
    callouts = set(re.findall(r"`([^`]+)`", callout_match.group(1))) if callout_match else set()
    return {"figures": figures, "callouts": callouts}


def generate_registry(repo_root: Path | None = None) -> dict[str, Any]:
    repo_root = (repo_root or Path(__file__).resolve().parents[2]).resolve()
    templates = repo_root / "latex_templates"
    class_text = (templates / "reportkit.cls").read_text(encoding="utf-8")
    class_match = re.search(r"\\ProvidesClass\{[^}]+\}\[[^]]+\s+v([^\s]+)", class_text)
    class_version = class_match.group(1) if class_match else "unknown"
    return {
        "figures": _figure_environments(templates),
        "callouts": _callouts(templates),
        "charts": _charts(repo_root / "python_scripts" / "reportkit_viz.py"),
        "commands": dict(COMMANDS),
        "class_version": class_version,
        "sources": {
            "figures": "latex_templates/reportkit*.sty",
            "callouts": "latex_templates/reportkit-boxes.sty",
            "charts": "python_scripts/reportkit_viz.py",
            "commands": "python_scripts/reportkit/registry.py",
        },
    }


def check_skill_drift(repo_root: Path | None = None) -> list[str]:
    repo_root = (repo_root or Path(__file__).resolve().parents[2]).resolve()
    registry = generate_registry(repo_root)
    inventory = skill_inventory(repo_root / "SKILL.md")
    errors: list[str] = []
    actual_figures = set(registry["figures"])
    if actual_figures != inventory["figures"]:
        errors.append(f"figure inventory drift: registry={sorted(actual_figures)}, SKILL.md={sorted(inventory['figures'])}")
    actual_callouts = set(registry["callouts"]["public"])
    if actual_callouts != inventory["callouts"]:
        errors.append(f"callout inventory drift: registry={sorted(actual_callouts)}, SKILL.md={sorted(inventory['callouts'])}")
    return errors
