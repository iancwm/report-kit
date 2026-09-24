#!/usr/bin/env python3
"""Run Pandoc and replace ReportKit visual sentinels with fragments."""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import sys

try:
    from _bootstrap import ensure_reportkit_importable
except ImportError:  # imported as publication_pipeline.scripts.render_visuals
    from ._bootstrap import ensure_reportkit_importable

ensure_reportkit_importable()

from reportkit.publication_validation import validate_publication  # noqa: E402

try:
    from image_rendering import replace_image_sentinel
except ImportError:  # imported as publication_pipeline.scripts.render_visuals
    from .image_rendering import replace_image_sentinel

SENTINEL_RE = re.compile(
    r"^\s*(?:\[\[|\{\[\}\{\[\})REPORTKIT-VISUAL:fig:"
    r"([a-z0-9]+(?:-[a-z0-9]+)*)"
    r"(?:\]\]|\{\]\}\{\]\})\s*$"
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manuscript", type=Path)
    parser.add_argument("fragments", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--source-root", type=Path, help="consumer publication root for image-slot validation")
    parser.add_argument("--profile", default="draft", help="validation profile (draft, final, or release)")
    args = parser.parse_args()
    source = args.manuscript.read_text(encoding="utf-8")
    image_slots = {}
    source_root: Path | None = args.source_root.resolve() if args.source_root else None
    if "REPORTKIT-IMAGE" in source:
        if source_root is None and args.manuscript.resolve().parent.name == "manuscript":
            source_root = args.manuscript.resolve().parent.parent
        if source_root is None:
            print("image slots require --source-root or a manuscript inside a project's manuscript/ directory", file=sys.stderr)
            return 2
        validation = validate_publication(source_root, profile=args.profile)
        if not validation.ok:
            for error in validation.errors:
                print(f"publication validation: {error}", file=sys.stderr)
            return 3
        image_slots = validation.image_slots
    proc = subprocess.run(["pandoc", "-f", "markdown", "-t", "latex", str(args.manuscript)], capture_output=True, text=True)
    if proc.returncode:
        print(proc.stderr or f"Pandoc failed for {args.manuscript}", file=sys.stderr)
        return proc.returncode
    output: list[str] = []
    for line in proc.stdout.splitlines():
        if source_root is not None:
            try:
                image = replace_image_sentinel(line, image_slots, source_root)
            except ValueError as exc:
                print(f"image rendering: {exc}", file=sys.stderr)
                return 3
            if image is not None:
                output.append(image[1])
                continue
        match = SENTINEL_RE.match(line)
        if not match:
            output.append(line)
            continue
        fragment = args.fragments / f"fig-{match.group(1)}.tex"
        if not fragment.is_file():
            print(f"missing fragment for fig:{match.group(1)}: {fragment}", file=sys.stderr)
            return 1
        output.append(fragment.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(output) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
