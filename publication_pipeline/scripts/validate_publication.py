#!/usr/bin/env python3
"""Validate manuscript order, visual sentinels, fragments, and labels."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

try:
    from _bootstrap import ensure_reportkit_importable
except ImportError:  # pragma: no cover - package execution path
    from ._bootstrap import ensure_reportkit_importable

ensure_reportkit_importable()

from reportkit.publication_validation import validate_publication


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "example_publication",
        help="consumer publication project (default: the pipeline's generic example)",
    )
    args = parser.parse_args()
    result = validate_publication(args.root)
    if result.ok:
        print(f"PASS: publication validation ({len(result.manuscript_files)} manuscripts, {len(result.slugs)} visuals, {len(result.labels)} labels)")
        return 0
    print("FAIL: publication validation", file=sys.stderr)
    for error in result.errors:
        print(f"- {error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
