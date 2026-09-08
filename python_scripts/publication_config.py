#!/usr/bin/env python3
"""Backward-compatible import path for ReportKit publication config."""
from pathlib import Path

from reportkit.config import *  # noqa: F401,F403


def main() -> int:
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
