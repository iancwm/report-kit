"""Structured, source-aware diagnostics for ReportKit TeX logs."""
from __future__ import annotations

from datetime import date
import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

DEFAULT_UNDERFULL_BADNESS = 4000
DIAGNOSTIC_TYPES = (
    "latex_error", "undefined_reference", "undefined_citation", "duplicate_label",
    "missing_asset", "missing_font", "missing_glyph", "overfull_hbox",
    "underfull_hbox", "bibliography_warning", "package_warning", "ignored_error",
)
LEGACY_TYPES = ("fatal", "undefined", "duplicate_label", "overfull", "underfull", "ignored_error", "allowlist")


def load_allowlist(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    entries = raw.get("entries", raw) if isinstance(raw, dict) else raw
    if not isinstance(entries, list):
        raise ValueError("allowlist must be a list or an object with entries")
    result: list[dict[str, str]] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or not all(key in entry for key in ("pattern", "reason", "expires")):
            raise ValueError(f"allowlist entry {index} needs pattern, reason, and expires")
        re.compile(str(entry["pattern"]))
        result.append({key: str(entry[key]) for key in ("pattern", "reason", "expires")})
    return result


def _logical_lines(text: str) -> list[tuple[int, str]]:
    """Return log lines plus the short wrapped windows TeX uses for messages."""
    raw = text.splitlines()
    records: list[tuple[int, str]] = []
    for index, line in enumerate(raw):
        stripped = line.strip()
        records.append((index + 1, line))
        if not stripped:
            continue
        if re.search(r"Overfull \\hbox|Underfull \\hbox", line):
            combined = line
            for continuation in raw[index + 1:index + 4]:
                if re.match(r"\s*(?:Overfull|Underfull|ignored error:|!\s|LaTeX Warning:|Package .* Warning:)", continuation):
                    break
                combined += " " + continuation.strip()
                if "too wide)" in combined or "badness " in combined or " in paragraph" in combined:
                    break
            if combined != line:
                records.append((index + 1, combined))
        elif re.search(r"(?:LaTeX Error|Package .* Warning|Reference .* undefined|Citation .* undefined)", line):
            combined = line
            for continuation in raw[index + 1:index + 3]:
                if continuation.startswith((" ", "l.", " ")):
                    combined += " " + continuation.strip()
            if combined != line:
                records.append((index + 1, combined))
    return records


def _file_stack(text: str) -> dict[int, str | None]:
    stack: list[str] = []
    locations: dict[int, str | None] = {}
    for line_number, line in enumerate(text.splitlines(), 1):
        locations[line_number] = stack[-1] if stack else None
        opens = re.findall(r"\((?:\./)?([^\s()]+\.(?:tex|sty|cls|def|fd|cfg|bib|md))", line)
        closes = line.count(")")
        for filename in opens:
            stack.append(filename)
        for _ in range(min(closes, len(stack))):
            stack.pop()
    return locations


def _owner(kind: str, filename: str | None) -> str:
    lowered = (filename or "").lower()
    if kind == "package_warning":
        return "TOOLCHAIN"
    if kind in {"missing_asset", "missing_font", "missing_glyph"}:
        return "ASSET"
    if kind in {"undefined_reference", "undefined_citation", "duplicate_label"}:
        return "CONTENT"
    if filename is None or lowered.startswith("body-") or "manuscript/" in lowered or "fragments/" in lowered or lowered.endswith(".md"):
        return "CONTENT"
    if re.search(r"(?:^|/)(?:reportkit[^/]*)\.(?:sty|cls)$", lowered):
        return "STYLE"
    if kind in {"latex_error", "ignored_error"}:
        return "BUILD"
    return "TOOLCHAIN"


def _relative_file(filename: str | None) -> str | None:
    if not filename:
        return None
    return filename.lstrip("./")


def _map_generated(filename: str | None, line: int | None, build_dir: Path | None) -> tuple[str | None, int | None]:
    if not filename or line is None or build_dir is None:
        return _relative_file(filename), line
    basename = Path(filename).name
    if not re.fullmatch(r"body-\d+\.tex", basename):
        return _relative_file(filename), line
    sidecar = build_dir / f"{Path(basename).stem}.map.json"
    if not sidecar.is_file():
        return _relative_file(filename), line
    try:
        mapping = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _relative_file(filename), line
    for fragment in mapping.get("fragments", []):
        start = int(fragment.get("generated_start", fragment.get("start", 0)))
        end = int(fragment.get("generated_end", fragment.get("end", 0)))
        if start <= line <= end:
            source_start = int(fragment.get("source_start", 1))
            return str(fragment.get("path", "fragments/" + fragment.get("slug", "fragment") + ".tex")), source_start + line - start
    source = mapping.get("source")
    return (str(source) if source else _relative_file(filename)), None


def _classify(message: str, underfull_badness: int) -> tuple[str | None, dict[str, Any]]:
    details: dict[str, Any] = {}
    if re.search(r"ignored error:", message, re.I):
        return "ignored_error", details
    if re.search(r"Missing character:", message):
        return "missing_glyph", details
    if re.search(r"(?:I can't find file|File .* not found|cannot be found)", message, re.I):
        if re.search(r"(?:font|\.tfm|\.pk|\.pfb)", message, re.I):
            return "missing_font", details
        return "missing_asset", details
    if re.search(r"(?:font .* not found|Font .* not loadable|\.tfm.*not found)", message, re.I):
        return "missing_font", details
    if re.search(r"Citation .* undefined|undefined citations", message, re.I):
        return "undefined_citation", details
    if re.search(r"Reference .* undefined|undefined references", message, re.I):
        return "undefined_reference", details
    if re.search(r"Label .* multiply defined|multiply defined", message, re.I):
        return "duplicate_label", details
    overfull = re.search(r"Overfull \\hbox \(([-+0-9.]+)pt too wide\)", message)
    if overfull:
        details["amount_pt"] = float(overfull.group(1))
        lines = re.search(r"at lines (\d+)(?:--(\d+))?", message)
        if lines:
            details["source_line"] = int(lines.group(1))
            if lines.group(2):
                details["line_end"] = int(lines.group(2))
        return "overfull_hbox", details
    underfull = re.search(r"Underfull \\hbox(?: \(badness (\d+)\))?", message)
    if underfull and int(underfull.group(1) or "10000") > underfull_badness:
        details["badness"] = int(underfull.group(1) or "10000")
        return "underfull_hbox", details
    if re.search(r"(?:biblatex|biber|bibtex|bibliography).*(?:Warning|undefined|please run)", message, re.I):
        return "bibliography_warning", details
    if re.search(r"^!\s|Emergency stop|Fatal error|Undefined control sequence|LaTeX Error:", message):
        return "latex_error", details
    if re.search(r"(?:Package .* Warning|LaTeX .* Warning:)", message):
        return "package_warning", details
    return None, details


def inspect_log(
    text: str,
    *,
    underfull_badness: int = DEFAULT_UNDERFULL_BADNESS,
    allowlist: list[dict[str, str]],
    source_root: Path | None = None,
    build_dir: Path | None = None,
) -> dict[str, Any]:
    counts: dict[str, int] = {key: 0 for key in DIAGNOSTIC_TYPES}
    counts.update({key: 0 for key in LEGACY_TYPES})
    issues: list[dict[str, Any]] = []
    stack = _file_stack(text)
    seen: set[tuple[int, str]] = set()
    legacy = {"latex_error": "fatal", "undefined_reference": "undefined", "undefined_citation": "undefined", "overfull_hbox": "overfull", "underfull_hbox": "underfull"}
    explicit = re.compile(r"(?:^|\s)([^\s:()]+\.(?:tex|sty|cls)):(\d+):")
    for log_line, message in _logical_lines(text):
        matched_allowlist = next((entry for entry in allowlist if re.search(entry["pattern"], message)), None)
        if matched_allowlist:
            if matched_allowlist["expires"] < date.today().isoformat():
                counts["allowlist"] += 1
                issues.append({"severity": "error", "type": "allowlist", "owner": "BUILD", "log_line": log_line, "message": f"expired allowlist entry: {message}"})
            continue
        kind, details = _classify(message, underfull_badness)
        if not kind or (log_line, kind) in seen:
            continue
        seen.add((log_line, kind))
        match = explicit.search(message)
        filename = match.group(1) if match else stack.get(log_line)
        source_line = int(match.group(2)) if match else details.pop("source_line", None)
        mapped_file, mapped_line = _map_generated(filename, source_line, build_dir)
        issue: dict[str, Any] = {
            "severity": "error" if kind in {"latex_error", "missing_asset", "missing_font", "missing_glyph", "ignored_error"} else "warning",
            "type": kind,
            "owner": _owner(kind, mapped_file or filename),
            "file": mapped_file,
            "log_line": log_line,
            "message": message.strip(),
        }
        if kind == "package_warning":
            issue["blocking"] = False
        if mapped_line is not None:
            issue["line"] = mapped_line
        issue.update(details)
        if source_root and issue.get("file"):
            candidate = Path(str(issue["file"]))
            if candidate.is_absolute():
                try:
                    issue["file"] = str(candidate.relative_to(source_root))
                except ValueError:
                    pass
        counts[kind] += 1
        if kind in legacy and legacy[kind] != kind:
            counts[legacy[kind]] += 1
        issues.append(issue)
    return {
        "passed": not any(issue.get("blocking", True) for issue in issues),
        "underfull_badness_threshold": underfull_badness,
        "counts": counts,
        "issues": issues,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--allowlist", type=Path, default=Path(__file__).resolve().parents[2] / "publication_pipeline/config/build-log-allowlist.json")
    parser.add_argument("--underfull-badness", type=int, default=DEFAULT_UNDERFULL_BADNESS)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--build-dir", type=Path)
    parser.add_argument("--json", dest="json_path", nargs="?", const=Path("-"), type=Path)
    args = parser.parse_args(argv)
    try:
        result = inspect_log(
            args.log.read_text(encoding="utf-8", errors="replace"),
            underfull_badness=args.underfull_badness,
            allowlist=load_allowlist(args.allowlist),
            source_root=args.source_root,
            build_dir=args.build_dir or args.log.parent,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: unable to inspect build log: {exc}", file=sys.stderr)
        return 1
    if args.json_path:
        serialized = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if str(args.json_path) == "-":
            print(serialized, end="")
        else:
            args.json_path.parent.mkdir(parents=True, exist_ok=True)
            args.json_path.write_text(serialized, encoding="utf-8")
    if result["passed"]:
        print("PASS: final TeX log passed the strict diagnostic gate")
        return 0
    print("FAIL: final TeX log contains actionable diagnostics", file=sys.stderr)
    for issue in result["issues"]:
        location = f"{issue.get('file') or '<unattributed>'}:{issue.get('line', issue.get('log_line'))}"
        print(f"- {location} [{issue['type']} / {issue['owner']}]: {issue['message']}", file=sys.stderr)
    return 1
