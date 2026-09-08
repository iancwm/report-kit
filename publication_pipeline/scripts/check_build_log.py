#!/usr/bin/env python3
"""Turn actionable TeX diagnostics into a deterministic build gate."""
from __future__ import annotations

import argparse
import json
import importlib.util
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON_ROOT = REPO_ROOT / "python_scripts"


def _load_reportkit_package() -> None:
    if "reportkit" in sys.modules:
        return
    package = PYTHON_ROOT / "reportkit"
    spec = importlib.util.spec_from_file_location(
        "reportkit", package / "__init__.py", submodule_search_locations=[str(package)]
    )
    if not spec or not spec.loader:
        raise ImportError(f"cannot load ReportKit package from {package}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["reportkit"] = module
    spec.loader.exec_module(module)


_load_reportkit_package()

from reportkit.diagnostics import (  # noqa: E402
    DEFAULT_UNDERFULL_BADNESS,
    inspect_log,
    load_allowlist,
    load_maps,
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
        print(f"FAIL: unable to inspect build log: {exc}", file=sys.stderr)
        return 1
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
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
