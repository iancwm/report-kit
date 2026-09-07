#!/usr/bin/env python3
"""Turn actionable TeX diagnostics into a deterministic build gate."""
from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import re
import sys

DEFAULT_UNDERFULL_BADNESS = 4000
DEFAULT_ALLOWLIST = Path(__file__).resolve().parents[1] / "config" / "build-log-allowlist.json"


def load_allowlist(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    entries = raw.get("entries", raw) if isinstance(raw, dict) else raw
    if not isinstance(entries, list):
        raise ValueError("allowlist must be a list or an object with entries")
    result = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or not all(key in entry for key in ("pattern", "reason", "expires")):
            raise ValueError(f"allowlist entry {index} needs pattern, reason, and expires")
        re.compile(str(entry["pattern"]))
        result.append({key: str(entry[key]) for key in ("pattern", "reason", "expires")})
    return result


def inspect_log(text: str, *, underfull_badness: int, allowlist: list[dict[str, str]]) -> dict:
    counts = {key: 0 for key in ("fatal", "undefined", "duplicate_label", "overfull", "underfull", "ignored_error", "allowlist")}
    issues: list[dict[str, object]] = []
    underfull = re.compile(r"Underfull \\hbox(?: \(badness (\d+)\))?")
    patterns = {
        "fatal": (re.compile(r"^!\s|Emergency stop|Fatal error|Undefined control sequence|LaTeX Error:"),),
        "undefined": (re.compile(r"Reference .* undefined|Citation .* undefined|There were undefined references|There were undefined citations"),),
        "duplicate_label": (re.compile(r"Label .* multiply defined"),),
        "overfull": (re.compile(r"Overfull \\hbox"),),
        "ignored_error": (re.compile(r"ignored error:"),),
    }
    for line_number, line in enumerate(text.splitlines(), 1):
        matched_allowlist = next((entry for entry in allowlist if re.search(entry["pattern"], line)), None)
        if matched_allowlist:
            if matched_allowlist["expires"] < date.today().isoformat():
                counts["allowlist"] += 1
                issues.append({"line": line_number, "kind": "allowlist", "text": f"expired: {line}"})
            continue
        kind = next((name for name, group in patterns.items() if any(pattern.search(line) for pattern in group)), None)
        match = underfull.search(line)
        if kind is None and match and int(match.group(1) or "10000") > underfull_badness:
            kind = "underfull"
        if kind:
            counts[kind] += 1
            issues.append({"line": line_number, "kind": kind, "text": line})
    return {"passed": not issues, "underfull_badness_threshold": underfull_badness, "counts": counts, "issues": issues}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--allowlist", type=Path, default=DEFAULT_ALLOWLIST)
    parser.add_argument("--underfull-badness", type=int, default=DEFAULT_UNDERFULL_BADNESS)
    parser.add_argument("--json", dest="json_path", type=Path)
    args = parser.parse_args()
    try:
        result = inspect_log(args.log.read_text(encoding="utf-8", errors="replace"), underfull_badness=args.underfull_badness, allowlist=load_allowlist(args.allowlist))
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
        print(f"- line {issue['line']} [{issue['kind']}]: {issue['text']}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
