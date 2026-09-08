"""Serve the resolved ReportKit context to humans and agents."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .config import load_publication_config, resolve_document
from .registry import generate_registry


def build_context(repo_root: Path, source_root: Path | None = None, profile: str | None = None) -> dict[str, Any]:
    config: dict[str, Any] = {}
    if source_root:
        config = load_publication_config(source_root / "publication.yaml")
    context = generate_registry(repo_root)
    document = resolve_document(config, profile) if config else {"main": "publication-template.tex", "class": "reportkit", "engine": "pdflatex"}
    context["document"] = document
    if source_root:
        context["publication"] = {"source_root": str(source_root.resolve()), "profile": profile or "default"}
    return context


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--profile")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = build_context(Path(__file__).resolve().parents[2], args.source_root, args.profile)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"ReportKit {result['version']} ({result['document']['engine']})")
        print(f"figures: {len(result['components']['figures'])}; callouts: {len(result['components']['callouts']['names'])}; charts: {len(result['components']['charts'])}")
    return 0
