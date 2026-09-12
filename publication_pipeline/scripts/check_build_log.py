#!/usr/bin/env python3
"""Turn actionable TeX diagnostics into a deterministic build gate."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]


try:
    from _bootstrap import ensure_reportkit_importable
except ImportError:  # imported as publication_pipeline.scripts.check_build_log
    from ._bootstrap import ensure_reportkit_importable

ensure_reportkit_importable()

from reportkit.diagnostics import (  # noqa: E402
    DEFAULT_UNDERFULL_BADNESS,
    diagnostic_envelope,
    inspect_log,
    load_allowlist,
    load_maps,
    make_diagnostic,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--allowlist", type=Path, default=REPO_ROOT / "publication_pipeline/config/build-log-allowlist.json")
    parser.add_argument("--underfull-badness", type=int, default=DEFAULT_UNDERFULL_BADNESS)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--map-dir", type=Path)
    parser.add_argument("--json", dest="json_path", type=Path)
    args = parser.parse_args()
    try:
        maps = load_maps(args.map_dir or args.log.parent)
        result = inspect_log(
            args.log.read_text(encoding="utf-8", errors="replace"),
            underfull_badness=args.underfull_badness,
            allowlist=load_allowlist(args.allowlist),
            maps=maps,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result = diagnostic_envelope([
            make_diagnostic("configuration_error", f"unable to inspect build log: {exc}", code="RK_LOG_INPUT")
        ], passed=False)
        if args.json_path:
            args.json_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"FAIL: unable to inspect build log: {exc}", file=sys.stderr)
        return 2
    if args.json_path:
        args.json_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if result["passed"]:
        print("PASS: final TeX log passed the strict diagnostic gate")
        return 0
    print("FAIL: final TeX log contains actionable diagnostics", file=sys.stderr)
    for issue in result["issues"]:
        location = issue.get("file") or "unknown source"
        if issue.get("line"):
            location += f":{issue['line']}"
        print(f"- {location} [{issue['type']} / {issue['owner']}]: {issue['message']}", file=sys.stderr)
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
