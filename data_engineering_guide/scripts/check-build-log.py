#!/usr/bin/env python3
"""Turn non-fatal TeX diagnostics into a deterministic build gate."""
from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import re
import sys


# Small underfull boxes are expected around deliberately breakable inline
# literals.  The document template uses the same threshold so diagnostics
# above this value remain visible and gate the build.
DEFAULT_UNDERFULL_BADNESS = 4000
DEFAULT_ALLOWLIST = Path(__file__).resolve().parents[1] / "config" / "build-log-allowlist.json"


def _load_allowlist(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    entries = raw.get("entries", raw) if isinstance(raw, dict) else raw
    if not isinstance(entries, list):
        raise ValueError("allowlist must be a JSON array or an object with an 'entries' array")
    validated: list[dict[str, str]] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or not all(key in entry for key in ("pattern", "reason", "expires")):
            raise ValueError(f"allowlist entry {index} needs pattern, reason, and expires")
        re.compile(str(entry["pattern"]))
        validated.append({key: str(entry[key]) for key in ("pattern", "reason", "expires")})
    return validated


def _allowlisted(line: str, allowlist: list[dict[str, str]]) -> tuple[bool, str | None]:
    for entry in allowlist:
        if re.search(entry["pattern"], line):
            if entry["expires"] < date.today().isoformat():
                return False, f"expired allowlist entry: {entry['reason']} (expired {entry['expires']})"
            return True, None
    return False, None


def inspect_log(text: str, *, underfull_badness: int, allowlist: list[dict[str, str]]) -> dict:
    issues: list[dict[str, object]] = []
    counts = {
        "fatal": 0,
        "undefined": 0,
        "duplicate_label": 0,
        "overfull": 0,
        "underfull": 0,
        "ignored_error": 0,
        "allowlist": 0,
    }
    underfull_re = re.compile(r"Underfull \\hbox(?: \(badness (\d+)\))?")
    undefined_patterns = (
        re.compile(r"Reference .* undefined"),
        re.compile(r"Citation .* undefined"),
        re.compile(r"There were undefined references"),
        re.compile(r"There were undefined citations"),
    )
    fatal_patterns = (
        re.compile(r"^!\s"),
        re.compile(r"Emergency stop"),
        re.compile(r"Fatal error"),
        re.compile(r"Undefined control sequence"),
        re.compile(r"LaTeX Error:"),
    )
    duplicate_label_pattern = re.compile(r"Label .* multiply defined")

    for line_number, line in enumerate(text.splitlines(), 1):
        allowlisted, allowlist_issue = _allowlisted(line, allowlist)
        if allowlist_issue:
            counts["allowlist"] += 1
            issues.append({"line": line_number, "kind": "allowlist", "message": allowlist_issue, "text": line})
            continue
        if allowlisted:
            continue

        kind: str | None = None
        if any(pattern.search(line) for pattern in fatal_patterns):
            kind = "fatal"
        elif duplicate_label_pattern.search(line):
            kind = "duplicate_label"
        elif any(pattern.search(line) for pattern in undefined_patterns):
            kind = "undefined"
        elif "Overfull \\hbox" in line:
            kind = "overfull"
        elif "ignored error:" in line:
            kind = "ignored_error"
        else:
            match = underfull_re.search(line)
            if match:
                badness = int(match.group(1) or "10000")
                if badness > underfull_badness:
                    kind = "underfull"
        if kind:
            counts[kind] += 1
            issues.append({"line": line_number, "kind": kind, "text": line})

    return {
        "passed": not issues,
        "underfull_badness_threshold": underfull_badness,
        "counts": counts,
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument(
        "--allowlist", type=Path, default=DEFAULT_ALLOWLIST, help="reviewed, expiry-dated diagnostic allowlist"
    )
    parser.add_argument(
        "--underfull-badness", type=int, default=DEFAULT_UNDERFULL_BADNESS, help="fail underfull boxes above this badness"
    )
    parser.add_argument("--json", dest="json_path", type=Path, help="write the gate result as JSON")
    args = parser.parse_args()
    try:
        allowlist = _load_allowlist(args.allowlist)
        result = inspect_log(
            args.log.read_text(encoding="utf-8", errors="replace"),
            underfull_badness=args.underfull_badness,
            allowlist=allowlist,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: unable to inspect build log: {exc}", file=sys.stderr)
        return 1

    if args.json_path:
        args.json_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if result["passed"]:
        print("PASS: final TeX log passed the strict diagnostic gate")
        return 0
    print("FAIL: final TeX log contains actionable diagnostics", file=sys.stderr)
    for issue in result["issues"]:
        print(f"- line {issue['line']} [{issue['kind']}]: {issue['text']}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
