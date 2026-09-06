#!/usr/bin/env python3
"""Validate the Data Engineering Guide before Pandoc or TeX runs."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from guide_validation import validate_guide


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="guide root (default: the parent of this script's directory)",
    )
    args = parser.parse_args()
    result = validate_guide(args.root)
    if result.ok:
        print(
            f"PASS: guide validation ({len(result.manuscript_files)} manuscripts, "
            f"{len(result.slugs)} visuals, {len(result.labels)} labels)"
        )
        return 0
    print("FAIL: guide validation", file=sys.stderr)
    for error in result.errors:
        print(f"- {error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
