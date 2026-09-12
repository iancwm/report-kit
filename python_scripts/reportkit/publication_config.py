"""Backward-compatible module for the dependency-free publication config."""
# This module deliberately re-exports the legacy public surface.
# ruff: noqa: F401
from __future__ import annotations

from pathlib import Path

from .config import (
    CONFIG_NAME, DOCUMENT_KEYS, IDENTITY_KEYS, KNOWN, LICENSE_KEYS, OUTPUT_KEYS,
    REQUIRED, SECTIONS, THEME_ENGINE_REQUIREMENTS, THEME_KEYS, VALIDATION_KEYS,
    load_publication_config, resolve_document, resolve_identity, resolve_license,
    resolve_output, resolve_theme, resolve_validation, slugify, theme_engine_conflict,
    theme_font_policy_conflict,
)


def main() -> int:
    """Validate a publication.yaml file from the command line."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate a publication.yaml file.")
    parser.add_argument("path", type=Path, nargs="?", default=Path(CONFIG_NAME))
    args = parser.parse_args()
    try:
        config = load_publication_config(args.path)
        if not config:
            print(f"FAIL: no publication config at {args.path}")
            return 1
        identity = resolve_identity(config, {}, args.path.parent)
    except (OSError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1
    print(f"PASS: {identity['title']} ({identity['slug']}) version {identity['version']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
