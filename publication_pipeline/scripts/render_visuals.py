#!/usr/bin/env python3
"""Run Pandoc and replace ReportKit visual sentinels with fragments."""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import sys

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
    args = parser.parse_args()
    proc = subprocess.run(["pandoc", "-f", "markdown", "-t", "latex", str(args.manuscript)], capture_output=True, text=True)
    if proc.returncode:
        print(proc.stderr or f"Pandoc failed for {args.manuscript}", file=sys.stderr)
        return proc.returncode
    output: list[str] = []
    for line in proc.stdout.splitlines():
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
