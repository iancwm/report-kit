"""Build the machine-readable ReportKit component registry from source files."""
from __future__ import annotations

import ast
from pathlib import Path
import re
import subprocess
from typing import Any

DIAGRAM_FILES = (
    "reportkit-diagrams.sty", "reportkit-spatial.sty", "reportkit-process.sty",
    "reportkit-structure.sty", "reportkit-grammar.sty",
)
PUBLIC_CHARTS = {
    "timeseries", "bar_chart", "distribution", "scatter_plot", "heatmap",
    "drawdown_chart", "waterfall_chart", "treemap_chart", "tornado_chart",
    "bubble_matrix", "timeline_chart",
}


def _environment_names(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return re.findall(r"\\NewDocumentEnvironment\{([^}]+)\}", text) + re.findall(r"\\newenvironment\{([^}]+)\}", text)


def _callouts(path: Path) -> tuple[list[str], dict[str, str]]:
    text = path.read_text(encoding="utf-8")
    names = re.findall(r"\\NewDocumentEnvironment\{([^}]+)\}", text)
    aliases: dict[str, str] = {}
    for alias, target in re.findall(r"\\NewDocumentEnvironment\{([^}]+)\}\{m\}.*?\\begin\{([^}]+)\}", text, re.S):
        if alias in {"evidence", "limitation", "tip"}:
            aliases[alias] = target
    public = [name for name in names if name not in aliases and name != "rk@callout"]
    return public, aliases


def _charts(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return sorted(
        node.name for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in PUBLIC_CHARTS
    )


def _git(repo_root: Path, *args: str) -> str:
    try:
        result = subprocess.run(["git", "-C", str(repo_root), *args], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def _class_version(path: Path) -> str:
    match = re.search(r"\\ProvidesClass\{reportkit\}\[[^]]*?v([0-9][^ ]*)", path.read_text(encoding="utf-8"))
    return match.group(1) if match else "unknown"


def skill_inventory(skill_path: Path) -> dict[str, set[str]]:
    text = skill_path.read_text(encoding="utf-8")
    visual_table = text.split("| Reader question", 1)[1].split("The distinction", 1)[0] if "| Reader question" in text else ""
    diagrams = set(re.findall(r"`([a-z][a-z0-9]+)`", visual_table))
    callout_line = next((line for line in text.splitlines() if "Use semantic callouts" in line), "")
    callouts = set(re.findall(r"`([a-z][a-z0-9]+)`", callout_line))
    return {"figures": diagrams, "callouts": callouts}


def generate_registry(repo_root: Path) -> dict[str, Any]:
    template_root = repo_root / "latex_templates"
    figures: list[str] = []
    for name in DIAGRAM_FILES:
        figures.extend(_environment_names(template_root / name))
    figures = sorted(set(figures) - {"diagram"})
    callouts, aliases = _callouts(template_root / "reportkit-boxes.sty")
    charts = _charts(repo_root / "python_scripts" / "reportkit_viz.py")
    git_version = _git(repo_root, "describe", "--tags", "--always")
    class_version = _class_version(template_root / "reportkit.cls")
    try:
        from .cli import build_parser
        parser = build_parser()
        commands = sorted(next(action for action in parser._actions if getattr(action, "choices", None) is not None).choices)
    except (AttributeError, ImportError):
        commands = ["doctor", "context", "check", "build", "diagnose", "inspect", "package", "analyse-history"]
    return {
        "version": git_version,
        "class_version": class_version,
        "version_check": {
            "git_describe": git_version,
            "class_version": class_version,
            "matches": git_version == class_version or git_version.startswith("v" + class_version),
        },
        "components": {
            "figures": figures,
            "callouts": {"names": sorted(callouts), "aliases": dict(sorted(aliases.items()))},
            "charts": charts,
        },
        "commands": commands,
    }
