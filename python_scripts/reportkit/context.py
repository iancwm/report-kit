"""Build the self-description returned by ``reportkit context``."""
from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Any

from .config import load_publication_config, resolve_document
from .registry import COMMANDS, generate_registry


def _git(repo_root: Path, *args: str) -> str:
    try:
        result = subprocess.run(["git", "-C", str(repo_root), *args], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return result.stdout.strip() if result.returncode == 0 and result.stdout.strip() else "unknown"


def build_context(repo_root: Path | None = None, source_root: Path | None = None, profile: str | None = None) -> dict[str, Any]:
    repo_root = (repo_root or Path(__file__).resolve().parents[2]).resolve()
    source_root = (source_root or repo_root / "publication_pipeline" / "example_publication").resolve()
    config_path = source_root / "publication.yaml"
    config = load_publication_config(config_path)
    registry = generate_registry(repo_root)
    version = _git(repo_root, "describe", "--tags", "--always")
    class_version = registry.pop("class_version")
    document = resolve_document(config, profile)
    result: dict[str, Any] = {
        "version": version,
        "document": {
            "engine": document.get("engine", "pdflatex"),
            "theme": document.get("theme", "default"),
            "publication_type": document.get("publication_type", "technical-report"),
            "paper": document.get("paper", "a4"),
        },
        "components": {
            "figures": registry.pop("figures"),
            "callouts": registry["callouts"]["public"],
            "callout_aliases": registry["callouts"]["aliases"],
            "charts": registry.pop("charts"),
        },
        "commands": dict(COMMANDS),
        "class_version": class_version,
    }
    if version != "unknown" and class_version != "unknown" and not version.endswith(class_version):
        result["version_warning"] = f"git ref {version} does not end with class version {class_version}"
    return result
