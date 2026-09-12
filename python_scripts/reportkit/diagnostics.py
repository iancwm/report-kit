"""Structured diagnostics for TeX build logs."""
from __future__ import annotations

from collections import Counter
from datetime import date
import difflib
import json
from pathlib import Path
import re
from typing import Any, Iterable

from .version import DIAGNOSTIC_SCHEMA_VERSION

DEFAULT_UNDERFULL_BADNESS = 4000

DIAGNOSTIC_DEFINITIONS: dict[str, dict[str, str]] = {
    "latex_error": {"severity": "error", "remediation": "Fix the reported LaTeX error at the authored source location."},
    "undefined_reference": {"severity": "warning", "remediation": "Define the referenced label or correct the reference name, then rebuild twice."},
    "undefined_citation": {"severity": "warning", "remediation": "Add the citation to the bibliography source or correct its key."},
    "duplicate_label": {"severity": "warning", "remediation": "Give every label a unique value and update its references."},
    "missing_asset": {"severity": "error", "remediation": "Add the asset inside the publication root or correct the relative path."},
    "missing_font": {"severity": "error", "remediation": "Install the pinned font set or select a theme whose fonts are available."},
    "missing_glyph": {"severity": "error", "remediation": "Use a verified script/font combination or provide a compatible font."},
    "overfull_hbox": {"severity": "warning", "remediation": "Shorten or reflow the content so it fits inside the declared layout."},
    "underfull_hbox": {"severity": "warning", "remediation": "Rephrase or adjust the content break to improve line filling."},
    "bibliography_warning": {"severity": "warning", "remediation": "Run the configured bibliography tool and rebuild, or remove the unused bibliography declaration."},
    "package_warning": {"severity": "warning", "remediation": "Review the package warning and resolve it or add a justified, expiring allowlist entry."},
    "ignored_error": {"severity": "error", "remediation": "Remove the ignored-error path and fix the underlying build failure."},
    "allowlist": {"severity": "error", "remediation": "Remove or renew the expired allowlist entry after reviewing the diagnostic."},
    "configuration_error": {"severity": "error", "remediation": "Correct the named configuration key or command argument and retry."},
    "publication_validation": {"severity": "error", "remediation": "Correct the publication source at the reported location and rerun reportkit check."},
    "contract_drift": {"severity": "error", "remediation": "Run reportkit docs --write, review the generated changes, and commit them."},
    "contract_version": {"severity": "error", "remediation": "Refresh reportkit context and retry with a compatible contract major version."},
    "deprecated_contract": {"severity": "warning", "remediation": "Refresh the cached context contract before the next major release."},
    "deprecated_primitive": {"severity": "warning", "remediation": "Replace the deprecated primitive with the alternative named in its contract entry."},
    "toolchain_mismatch": {"severity": "error", "remediation": "Run the command in the pinned ReportKit OCI toolchain or update the lock and baselines together."},
    "environment_error": {"severity": "error", "remediation": "Install or select the required pinned build dependency, then rerun reportkit doctor."},
    "compile_timeout": {"severity": "error", "remediation": "Fix the non-terminating input or have a trusted operator raise the compile timeout."},
    "compile_memory": {"severity": "error", "remediation": "Reduce document memory use or have a trusted operator raise the memory limit."},
    "compile_failure": {"severity": "error", "remediation": "Inspect the structured TeX diagnostics and correct the authored source."},
    "pdf_geometry": {"severity": "error", "remediation": "Adjust the content or primitive so every object remains within the page media box."},
    "blank_page": {"severity": "error", "remediation": "Remove the unintended page break or add the missing page content."},
    "visual_regression": {"severity": "error", "remediation": "Review the rendered difference; fix the regression or explicitly regenerate the pinned baseline."},
    "security_violation": {"severity": "error", "remediation": "Use paths inside the publication root and do not enable shell escape."},
    "internal_error": {"severity": "error", "remediation": "Report the failure with the command output and ReportKit revision."},
}

DIAGNOSTIC_TYPES = tuple(DIAGNOSTIC_DEFINITIONS)


def _diagnostic_code(kind: str, rule: str | None = None) -> str:
    suffix = rule or kind
    return "RK_" + re.sub(r"[^A-Z0-9]+", "_", suffix.upper()).strip("_")


for _name, _definition in DIAGNOSTIC_DEFINITIONS.items():
    _definition.setdefault("code", _diagnostic_code(_name))
    _definition.setdefault("type", _name)
    _definition.setdefault("docs", "references/agent-contract.md#diagnostic-envelope-and-exits")


def suggest(value: str, choices: Iterable[str], *, limit: int = 3) -> list[str]:
    """Return deterministic near-match suggestions for an unrecognised name."""
    return difflib.get_close_matches(value, sorted(set(choices)), n=limit, cutoff=0.45)


def make_diagnostic(
    kind: str,
    message: str,
    *,
    code: str | None = None,
    severity: str | None = None,
    remediation: str | None = None,
    primitive: str | None = None,
    source: dict[str, Any] | None = None,
    docs: str | None = None,
    candidates: Iterable[str] = (),
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create one record in the stable diagnostic schema."""
    definition = DIAGNOSTIC_DEFINITIONS.get(kind, DIAGNOSTIC_DEFINITIONS["internal_error"])
    normalized_source = None if source is None else {
        "file": source.get("file"),
        "line": source.get("line"),
        "line_end": source.get("line_end"),
    }
    item: dict[str, Any] = {
        "code": code or definition["code"],
        "type": definition["type"],
        "severity": severity or definition["severity"],
        "message": re.sub(r"\s+", " ", str(message)).strip(),
        "remediation": remediation or definition["remediation"],
        "primitive": primitive,
        "source": normalized_source,
        "docs": docs or definition["docs"],
        "candidates": list(candidates),
        "details": dict(details or {}),
    }
    # Flat aliases are retained throughout ReportKit v1.x.
    item["file"] = normalized_source.get("file") if normalized_source else None
    item["line"] = normalized_source.get("line") if normalized_source else None
    item["line_end"] = normalized_source.get("line_end") if normalized_source else None
    item["kind"] = _legacy_kind(kind)
    item["owner"] = item["details"].get("owner", _owner(kind, item["file"]))
    item["blocking"] = item["severity"] == "error"
    return item


def diagnostic_envelope(
    diagnostics: Iterable[dict[str, Any]],
    *,
    passed: bool | None = None,
    **payload: Any,
) -> dict[str, Any]:
    records = list(diagnostics)
    result = {
        "schema_version": DIAGNOSTIC_SCHEMA_VERSION,
        "passed": not any(item.get("severity") == "error" for item in records) if passed is None else passed,
        "diagnostics": records,
        **payload,
    }
    # ``issues`` is the v1.5 diagnostic-list name.
    result.setdefault("issues", records)
    result.setdefault("errors", [item["message"] for item in records if item.get("severity") == "error"])
    return result

_FILE_LINE = re.compile(r"(?P<file>(?:\./|[^()\s]*[/\\])?[^()\s]+\.tex):(?P<line>\d+):")
_STACK_FILE = re.compile(r"\((?P<file>(?:\./|/)[^()\s]+\.[A-Za-z0-9]+)(?=\s|\)|$)")
_OVERFULL = re.compile(
    r"Overfull\s+\\hbox\s*\((?P<amount>[0-9]+(?:\.[0-9]+)?)pt\s+too\s+wide\)"
    r"(?:\s+in\s+paragraph\s+at\s+lines\s+(?P<line>\d+)(?:--(?P<line_end>\d+))?)?",
    re.IGNORECASE,
)
_UNDERFULL = re.compile(r"Underfull\s+\\hbox(?:\s*\(badness\s+(?P<badness>\d+)\))?", re.IGNORECASE)


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
        pattern = str(entry["pattern"])
        re.compile(pattern)
        result.append({key: str(entry[key]) for key in ("pattern", "reason", "expires")})
    return result


def load_maps(map_dir: Path | None) -> dict[str, dict[str, Any]]:
    if not map_dir or not map_dir.is_dir():
        return {}
    maps: dict[str, dict[str, Any]] = {}
    for path in map_dir.glob("body-*.map.json"):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(value, dict):
            maps[path.name.removesuffix(".map.json") + ".tex"] = value
            maps[path.stem.removesuffix(".map") + ".tex"] = value
    return maps


def _normalise_file(value: str | None) -> str | None:
    if not value:
        return None
    return value.replace("\\", "/").removeprefix("./")


def _map_location(file_name: str | None, line: int | None, maps: dict[str, dict[str, Any]]) -> tuple[str | None, int | None, int | None]:
    normalised = _normalise_file(file_name)
    if not normalised or line is None:
        return normalised, None, None
    mapping = maps.get(normalised) or maps.get(Path(normalised).name)
    if not mapping:
        return normalised, line, None
    for fragment in mapping.get("fragments", []):
        if not isinstance(fragment, dict):
            continue
        start = fragment.get("generated_start", fragment.get("start"))
        end = fragment.get("generated_end", fragment.get("end"))
        if isinstance(start, int) and isinstance(end, int) and start <= line <= end:
            fragment_start = fragment.get("fragment_start", 1)
            if not isinstance(fragment_start, int):
                fragment_start = 1
            return str(fragment.get("path")), fragment_start + line - start, None
    return str(mapping.get("source", normalised)), None, None


def _owner(kind: str, file_name: str | None) -> str:
    file_value = (file_name or "").replace("\\", "/")
    if kind in {"missing_asset", "missing_font", "missing_glyph"}:
        return "ASSET"
    if kind in {"latex_error", "ignored_error"}:
        return "BUILD"
    if kind in {"undefined_reference", "undefined_citation", "duplicate_label", "overfull_hbox", "underfull_hbox"}:
        return "CONTENT" if (not file_value or file_value.startswith("body-") or "manuscript/" in file_value or "fragments/" in file_value) else "STYLE"
    if file_value.endswith((".cls", ".sty")) or "/reportkit" in file_value:
        return "STYLE"
    if kind in {"package_warning", "bibliography_warning"}:
        return "TOOLCHAIN"
    return "BUILD"


def _legacy_kind(kind: str) -> str:
    return {
        "latex_error": "fatal", "undefined_reference": "undefined", "undefined_citation": "undefined",
        "duplicate_label": "duplicate_label", "overfull_hbox": "overfull", "underfull_hbox": "underfull",
    }.get(kind, kind)


def _new_counts() -> Counter[str]:
    return Counter({name: 0 for name in (
        "fatal", "undefined", "duplicate_label", "overfull", "underfull", "ignored_error", "allowlist",
        *DIAGNOSTIC_TYPES,
    )})


def _line_for_offset(offset: int, starts: list[int]) -> int:
    line = 1
    for index, start in enumerate(starts):
        if start > offset:
            break
        line = index + 1
    return line


def _physical_context(lines: list[str]) -> list[str | None]:
    stack: list[str] = []
    result: list[str | None] = []
    for raw in lines:
        result.append(stack[-1] if stack else None)
        opens = list(_STACK_FILE.finditer(raw))
        for match in opens:
            stack.append(_normalise_file(match.group("file")) or match.group("file"))
        close_count = 0
        if opens:
            close_count = max(0, raw.count(")") - raw.count("\\)"))
        elif raw.strip().startswith(")"):
            close_count = max(0, raw.count(")") - raw.count("\\)"))
        for _ in range(min(close_count, len(stack))):
            stack.pop()
    return result


def _message(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def inspect_log(
    text: str,
    *,
    underfull_badness: int = DEFAULT_UNDERFULL_BADNESS,
    allowlist: list[dict[str, str]] | None = None,
    maps: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return deterministic, source-aware diagnostics for a TeX log."""
    lines = text.splitlines()
    contexts = _physical_context(lines)
    starts: list[int] = []
    flat_parts: list[str] = []
    cursor = 0
    for line in lines:
        starts.append(cursor)
        flat_parts.append(line)
        cursor += len(line) + 1
    flat = " ".join(flat_parts)
    allowlist = allowlist or []
    maps = maps or {}
    counts = _new_counts()
    issues: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()

    def add(kind: str, offset: int, raw_message: str, *, line: int | None = None, line_end: int | None = None, amount_pt: float | None = None) -> None:
        physical_line = _line_for_offset(offset, starts) if starts else 1
        key = (kind, physical_line)
        if key in seen:
            return
        seen.add(key)
        file_name = contexts[physical_line - 1] if contexts and physical_line <= len(contexts) else None
        file_match = _FILE_LINE.search(raw_message)
        if file_match:
            file_name = _normalise_file(file_match.group("file"))
            if line is None:
                line = int(file_match.group("line"))
        mapped_file, mapped_line, mapped_end = _map_location(file_name, line, maps)
        if mapped_file and mapped_file.startswith("body-") and line is None:
            mapped_file = (maps.get(mapped_file) or {}).get("source", mapped_file)
        legacy = _legacy_kind(kind)
        counts[kind] += 1
        if legacy != kind:
            counts[legacy] += 1
        mapped_line_end = None
        if line_end is not None and mapped_line is not None:
            mapped_line_end = line_end if mapped_file == file_name else mapped_line + (line_end - (line or line_end))
        source = None
        if mapped_file:
            source = {"file": mapped_file}
            if mapped_line is not None:
                source["line"] = mapped_line
            if mapped_line_end is not None:
                source["line_end"] = mapped_line_end
        item = make_diagnostic(
            kind,
            _message(raw_message),
            source=source,
            details={
                "log_line": physical_line,
                "owner": _owner(kind, mapped_file),
            },
        )
        item.update({
            "kind": legacy,
            "file": mapped_file,
            "log_line": physical_line,
            "owner": _owner(kind, mapped_file),
            # Historical behavior treated every record except package warnings
            # as blocking, including layout warnings.
            "blocking": kind != "package_warning",
        })
        if amount_pt is not None:
            item["amount_pt"] = amount_pt
            item["details"]["amount_pt"] = amount_pt
        issues.append(item)

    allowlisted_lines: set[int] = set()
    for physical_line, raw in enumerate(lines, 1):
        match = next((entry for entry in allowlist if re.search(entry["pattern"], raw)), None)
        if not match:
            continue
        allowlisted_lines.add(physical_line)
        if match["expires"] < date.today().isoformat():
            add("allowlist", starts[physical_line - 1], f"expired: {raw}")

    for match in _OVERFULL.finditer(flat):
        start_line = int(match.group("line")) if match.group("line") else None
        end_line = int(match.group("line_end")) if match.group("line_end") else None
        physical_line = _line_for_offset(match.start(), starts) if starts else 1
        if physical_line not in allowlisted_lines:
            raw_line = lines[physical_line - 1] if lines else match.group(0)
            explicit = _FILE_LINE.search(raw_line)
            if explicit and start_line is None:
                start_line = int(explicit.group("line"))
            add("overfull_hbox", match.start(), raw_line if explicit else match.group(0), line=start_line, line_end=end_line, amount_pt=float(match.group("amount")))
    for match in _UNDERFULL.finditer(flat):
        badness = int(match.group("badness") or "10000")
        physical_line = _line_for_offset(match.start(), starts) if starts else 1
        if badness > underfull_badness and physical_line not in allowlisted_lines:
            add("underfull_hbox", match.start(), match.group(0))

    line_patterns: Iterable[tuple[str, re.Pattern[str]]] = (
        ("ignored_error", re.compile(r"ignored error:", re.IGNORECASE)),
        ("undefined_reference", re.compile(r"Reference .*? undefined|There were undefined references", re.IGNORECASE)),
        ("undefined_citation", re.compile(r"Citation .*? undefined|There were undefined citations", re.IGNORECASE)),
        ("duplicate_label", re.compile(r"Label .*? multiply defined", re.IGNORECASE)),
        ("missing_font", re.compile(r"(?:font|Font|metric) .*?(?:not found|not loadable)|libertinus.*?not found", re.IGNORECASE)),
        ("missing_glyph", re.compile(r"Missing character:", re.IGNORECASE)),
        ("missing_asset", re.compile(r"(?:File .*? not found|cannot be found|I can't find file|missing asset)", re.IGNORECASE)),
        ("bibliography_warning", re.compile(r"No file .*?\.bbl|BibTeX|biber", re.IGNORECASE)),
        ("latex_error", re.compile(r"^!\s|Emergency stop|Fatal error|Undefined control sequence|LaTeX Error:", re.IGNORECASE)),
        ("package_warning", re.compile(r"Package .*? Warning:", re.IGNORECASE)),
    )
    for physical_line, raw in enumerate(lines, 1):
        if physical_line in allowlisted_lines:
            continue
        for kind, pattern in line_patterns:
            if pattern.search(raw):
                add(kind, starts[physical_line - 1], raw)
                break
    issues.sort(key=lambda issue: (issue["log_line"], issue["type"]))
    return diagnostic_envelope(
        issues,
        passed=not any(issue["blocking"] for issue in issues),
        underfull_badness_threshold=underfull_badness,
        counts=dict(counts),
    )
