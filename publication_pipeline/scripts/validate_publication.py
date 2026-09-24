#!/usr/bin/env python3
"""Validate manuscript order, diagram/image sentinels, declarations, and labels."""
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
    parser.add_argument(
        "--profile",
        choices=("draft", "final", "release"),
        default="draft",
        help="validation profile; final and release require supplied images and resolved rights",
    )
    args = parser.parse_args()
    result = validate_publication(args.root, profile=args.profile)
    if result.ok:
        print(f"PASS: publication validation ({len(result.manuscript_files)} manuscripts, {len(result.slugs)} visuals, {len(result.image_slots)} image slots, {len(result.labels)} labels)")
        for diagnostic in result.diagnostics:
            if diagnostic["severity"] == "warning":
                print(f"WARN [{diagnostic['code']}]: {diagnostic['message']}", file=sys.stderr)
        return 0
    print("FAIL: publication validation", file=sys.stderr)
    for diagnostic in result.diagnostics:
        print(f"- [{diagnostic['severity'].upper()} {diagnostic['code']}] {diagnostic['message']}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
