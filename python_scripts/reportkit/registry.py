"""Machine-readable inventory of ReportKit's public authoring primitives."""
from __future__ import annotations

import ast
import json
from pathlib import Path
import re
from typing import Any, Iterable

from .publications import availability_for

CALLOUT_ALIASES = {"evidence": "evidencenote", "limitation": "limitationnote", "tip": "tipnote"}
FIGURE_ENVIRONMENTS = {
    "capabilitymap", "causalloop", "continuum", "evidencestack", "maturitymodel",
    "reportarchitecture", "reportcompare", "reportcycle", "reportflow", "reportfunnel",
    "reportmatrix", "reportnetwork", "reportroadmap", "reportstate", "reportswimlane",
    "reporttimeline", "reporttree", "riskheatmap", "strategicpillars",
}
CALLOUT_ENVIRONMENTS = {
    "principle", "decisionpoint", "researchproblem", "assumption", "redflag",
    "evidencenote", "limitationnote", "tipnote", "deliverablenote", "metric",
    *CALLOUT_ALIASES,
}
PUBLIC_CHART_NAMES = {
    "timeseries", "bar_chart", "distribution", "scatter_plot", "heatmap", "drawdown_chart",
    "risk_reward_chart", "donut_chart", "waterfall_chart", "treemap_chart", "tornado_chart",
    "bubble_matrix", "timeline_chart",
}
LEGACY_CHART_NAMES = PUBLIC_CHART_NAMES - {"donut_chart", "risk_reward_chart"}
PRIMITIVE_KINDS = ("callout", "figure", "chart", "composition", "command")
COMMANDS = {
    "doctor": "reportkit doctor", "context": "reportkit context", "check": "reportkit check",
    "build": "reportkit build", "diagnose": "reportkit diagnose", "inspect": "reportkit inspect",
    "package": "reportkit package", "analyse-history": "reportkit analyse-history", "docs": "reportkit docs",
}
COMMAND_CONTRACT: dict[str, dict[str, Any]] = {
    "doctor": {"summary": "Inspect build dependencies and pinned-toolchain drift.", "arguments": ["--require", "--json"], "exit_codes": [0, 5, 70]},
    "context": {"summary": "Print the versioned ReportKit capability contract.", "arguments": ["--source-root", "--output-root", "--profile", "--publication-type", "--theme", "--kind", "--schema", "--json"], "exit_codes": [0, 2, 70]},
    "check": {"summary": "Validate publication structure without invoking TeX.", "arguments": ["--source-root", "--output-root", "--profile", "--engine", "--contract-version", "--json"], "exit_codes": [0, 2, 3, 70]},
    "build": {"summary": "Validate, convert, compile, diagnose, render, and inspect a publication.", "arguments": ["--source-root", "--output-root", "--profile", "--mode", "--section", "--chapter", "--engine", "--title", "--author", "--version", "--cover", "--contract-version", "--compile-timeout-seconds", "--memory-limit-mb", "--json"], "exit_codes": [0, 2, 3, 4, 5, 70]},
    "diagnose": {"summary": "Parse a TeX log into source-aware diagnostics.", "arguments": ["log", "--source-root", "--output-root", "--profile", "--allowlist", "--underfull-badness", "--json"], "exit_codes": [0, 2, 3, 70]},
    "inspect": {"summary": "Inspect PDF geometry, metadata, fonts, links, and bookmarks.", "arguments": ["pdf", "--source-root", "--output-root", "--profile", "--json"], "exit_codes": [0, 2, 3, 5, 70]},
    "package": {"summary": "Package a passing combined build.", "arguments": ["--source-root", "--output-root", "--profile", "--build-dir", "--destination", "--json"], "exit_codes": [0, 2, 3, 70]},
    "analyse-history": {"summary": "Summarize recurring diagnostics in build history.", "arguments": ["--source-root", "--history-dir", "--json"], "exit_codes": [0, 2, 70]},
    "docs": {"summary": "Write or check contract-derived reference sections.", "arguments": ["--write", "--check", "--json"], "exit_codes": [0, 2, 3, 70]},
}

_LATEX_DECLARATION = re.compile(
    r"\\(?P<form>NewDocumentEnvironment|NewDocumentCommand|ProvideDocumentCommand)\s*\{",
    re.MULTILINE,
)
_CONTRACT_BLOCK = re.compile(
    r"(?ms)^[ \t]*%[ \t]*<reportkit-contract>[ \t]*\n"
    r"(?P<body>(?:^[ \t]*%[^\n]*\n)+?)"
    r"^[ \t]*%[ \t]*</reportkit-contract>[ \t]*\n?"
)
_PY_CONTRACT_BLOCK = re.compile(
    r"(?ms)^[ \t]*\#[ \t]*<reportkit-contract>[ \t]*\n"
    r"(?P<body>(?:^[ \t]*\#[^\n]*\n)+?)"
    r"^[ \t]*\#[ \t]*</reportkit-contract>[ \t]*\n?"
)
_INTERNAL_MARKER = re.compile(r"(?m)^[ \t]*%[ \t]*reportkit-contract:[ \t]*internal[ \t]*$")


class ContractError(ValueError):
    """Raised when source-adjacent contract metadata is invalid."""


def _balanced_group(text: str, start: int) -> tuple[str, int]:
    if start >= len(text) or text[start] != "{":
        raise ContractError("expected a braced group")
    depth = 0
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1:index], index + 1
    raise ContractError("unterminated braced group")


def parse_xparse_signature(spec: str) -> list[dict[str, Any]]:
    """Normalize supported xparse specifiers, including nested defaults."""
    result: list[dict[str, Any]] = []
    index = 0
    position = 0
    while index < len(spec):
        if spec[index].isspace():
            index += 1
            continue
        token = spec[index]
        index += 1
        position += 1
        if token == "m":
            result.append({"position": position, "specifier": "m", "required": True, "default": None})
        elif token == "o":
            result.append({"position": position, "specifier": "o", "required": False, "default": None})
        elif token == "s":
            result.append({"position": position, "specifier": "s", "required": False, "default": False})
        elif token == "O":
            while index < len(spec) and spec[index].isspace():
                index += 1
            default, index = _balanced_group(spec, index)
            result.append({"position": position, "specifier": "O", "required": False, "default": default})
        else:
            raise ContractError(f"unsupported xparse argument specifier {token!r} in {spec!r}")
    return result


def _metadata_blocks(text: str, *, python: bool = False) -> list[tuple[int, int, dict[str, Any]]]:
    pattern = _PY_CONTRACT_BLOCK if python else _CONTRACT_BLOCK
    prefix = "#" if python else "%"
    blocks: list[tuple[int, int, dict[str, Any]]] = []
    for match in pattern.finditer(text):
        lines = []
        for raw in match.group("body").splitlines():
            value = raw.lstrip()
            if value.startswith(prefix):
                lines.append(value[1:].lstrip())
        try:
            payload = json.loads("\n".join(lines))
        except json.JSONDecodeError as exc:
            line = text.count("\n", 0, match.start()) + exc.lineno
            raise ContractError(f"invalid contract JSON at line {line}: {exc.msg}") from exc
        if not isinstance(payload, dict):
            raise ContractError("contract metadata must be a JSON object")
        blocks.append((match.start(), match.end(), payload))
    return blocks


def _adjacent_metadata(text: str, position: int, blocks: Iterable[tuple[int, int, dict[str, Any]]]) -> dict[str, Any] | None:
    adjacent = [payload for _, end, payload in blocks if end <= position and not text[end:position].strip()]
    return adjacent[-1] if adjacent else None


def _has_adjacent_internal_marker(text: str, position: int) -> bool:
    markers = [match for match in _INTERNAL_MARKER.finditer(text, 0, position)]
    return bool(markers and not text[markers[-1].end():position].strip())


def _default_availability(path: Path) -> dict[str, list[str]]:
    if path.parent.name == "publication_types" and "equity-research" in path.name:
        return availability_for(publication_type="equity-research")
    if path.parent.name == "themes":
        theme = path.stem.removeprefix("reportkit-theme-")
        publication = "equity-research" if theme == "institutional-research" else "technical-report"
        return availability_for(publication_type=publication)
    return availability_for()


def _kind_for_environment(name: str) -> str:
    if name in CALLOUT_ENVIRONMENTS or name == "execsummary":
        return "callout"
    if name in FIGURE_ENVIRONMENTS:
        return "figure"
    return "composition"


def _pointer(kind: str, name: str) -> str:
    return f"#/capabilities/primitives/{kind}/{name}"


def _default_latex_example(name: str, form: str, arguments: list[dict[str, Any]]) -> str:
    values = []
    for argument in arguments:
        if argument["required"]:
            values.append("{Example}")
        elif argument["specifier"] == "s":
            values.append("*")
        else:
            values.append("[]")
    invocation = "".join(values)
    if form.endswith("Environment"):
        return f"\\begin{{{name}}}{invocation}\nExample content.\n\\end{{{name}}}"
    return f"\\{name}{invocation}"


def _normalise_latex_record(
    *, name: str, form: str, spec: str, metadata: dict[str, Any] | None,
    path: Path, repo_root: Path, line: int,
) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    if metadata is None:
        metadata = {}
        errors.append(f"{path.relative_to(repo_root)}:{line}: public primitive {name!r} has no adjacent contract metadata")
    kind = str(metadata.get("kind") or (_kind_for_environment(name) if form.endswith("Environment") else "command"))
    if kind not in PRIMITIVE_KINDS:
        errors.append(f"{path.relative_to(repo_root)}:{line}: primitive {name!r} has invalid kind {kind!r}")
        kind = "command"
    parsed = parse_xparse_signature(spec)
    declared_arguments = metadata.get("arguments", [])
    if not isinstance(declared_arguments, list):
        declared_arguments = []
        errors.append(f"{path.relative_to(repo_root)}:{line}: primitive {name!r} arguments must be a list")
    if len(declared_arguments) != len(parsed):
        errors.append(
            f"{path.relative_to(repo_root)}:{line}: primitive {name!r} metadata declares "
            f"{len(declared_arguments)} arguments but signature has {len(parsed)}"
        )
    arguments = []
    for index, syntax in enumerate(parsed):
        declared = declared_arguments[index] if index < len(declared_arguments) and isinstance(declared_arguments[index], dict) else {}
        argument = {
            **syntax,
            "name": str(declared.get("name") or f"argument_{index + 1}"),
            "type": str(declared.get("type") or ("options" if syntax["specifier"] in {"O", "o"} else "text")),
            "description": str(declared.get("description") or "Undocumented argument."),
        }
        if "default" in declared and declared["default"] != syntax["default"]:
            errors.append(f"{path.relative_to(repo_root)}:{line}: primitive {name!r} argument {index + 1} default disagrees with xparse")
        arguments.append(argument)
    required = sum(bool(value["required"]) for value in parsed)
    record = {
        "name": name, "kind": kind, "signature": " ".join(spec.split()), "source_signature": spec,
        "arity": {"required": required, "optional": len(parsed) - required}, "arguments": arguments,
        "constraints": metadata.get("constraints", []),
        "example": metadata.get("example") or _default_latex_example(name, form, parsed),
        "available_in": metadata.get("available_in") or _default_availability(path),
        "stability": metadata.get("stability", "stable"), "since": metadata.get("since", "1.0.0"),
        "description": metadata.get("description") or name.replace("-", " ").replace("_", " ").title(),
        "contract_pointer": _pointer(kind, name), "docs": _pointer(kind, name),
        "source": {"file": str(path.relative_to(repo_root)), "line": line},
    }
    if metadata.get("parent"):
        record["parent"] = metadata["parent"]
    return record, errors


def _latex_primitives(path: Path, repo_root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    text = path.read_text(encoding="utf-8")
    try:
        blocks = _metadata_blocks(text)
    except ContractError as exc:
        return [], [f"{path.relative_to(repo_root)}: {exc}"]
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    for match in _LATEX_DECLARATION.finditer(text):
        name_raw, next_index = _balanced_group(text, match.end() - 1)
        while next_index < len(text) and text[next_index].isspace():
            next_index += 1
        spec, _ = _balanced_group(text, next_index)
        name = name_raw.lstrip("\\")
        if "@" in name:
            if not _has_adjacent_internal_marker(text, match.start()):
                line = text.count("\n", 0, match.start()) + 1
                errors.append(
                    f"{path.relative_to(repo_root)}:{line}: non-public declaration {name!r} "
                    "needs an adjacent reportkit-contract: internal marker"
                )
            continue
        line = text.count("\n", 0, match.start()) + 1
        try:
            record, record_errors = _normalise_latex_record(
                name=name, form=match.group("form"), spec=spec,
                metadata=_adjacent_metadata(text, match.start(), blocks), path=path, repo_root=repo_root, line=line,
            )
        except ContractError as exc:
            errors.append(f"{path.relative_to(repo_root)}:{line}: {exc}")
            continue
        records.append(record)
        errors.extend(record_errors)
    return records, errors


def _python_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[str, list[dict[str, Any]]]:
    args = node.args
    positional = [*args.posonlyargs, *args.args]
    default_offset = len(positional) - len(args.defaults)
    arguments: list[dict[str, Any]] = []
    parts: list[str] = []
    for index, argument in enumerate(positional):
        required = index < default_offset
        default = None if required else ast.unparse(args.defaults[index - default_offset])
        arguments.append({"name": argument.arg, "required": required, "default": default, "specifier": "positional"})
        parts.append(argument.arg if required else f"{argument.arg}={default}")
    if args.kwonlyargs:
        parts.append("*")
    for argument, default_node in zip(args.kwonlyargs, args.kw_defaults):
        required = default_node is None
        default = None if required else ast.unparse(default_node)
        arguments.append({"name": argument.arg, "required": required, "default": default, "specifier": "keyword"})
        parts.append(argument.arg if required else f"{argument.arg}={default}")
    return ", ".join(parts), arguments


def _chart_primitives(path: Path, repo_root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    text = path.read_text(encoding="utf-8")
    try:
        blocks = _metadata_blocks(text, python=True)
    except ContractError as exc:
        return [], [f"{path.relative_to(repo_root)}: {exc}"]
    tree = ast.parse(text)
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    lines = text.splitlines(keepends=True)
    offsets = [0]
    for value in lines:
        offsets.append(offsets[-1] + len(value))
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or node.name not in PUBLIC_CHART_NAMES:
            continue
        position = offsets[node.lineno - 1]
        metadata = _adjacent_metadata(text, position, blocks)
        if metadata is None:
            metadata = {}
            errors.append(f"{path.relative_to(repo_root)}:{node.lineno}: chart {node.name!r} has no adjacent contract metadata")
        signature, parsed = _python_signature(node)
        declared_arguments = metadata.get("arguments", [])
        if not isinstance(declared_arguments, list):
            declared_arguments = []
        by_name = {str(item.get("name")): item for item in declared_arguments if isinstance(item, dict) and item.get("name")}
        arguments = [{
            **value,
            "type": by_name.get(value["name"], {}).get("type", "any"),
            "description": by_name.get(value["name"], {}).get("description", "Chart input or option."),
        } for value in parsed]
        missing = [value["name"] for value in parsed if value["name"] not in by_name]
        if missing:
            errors.append(f"{path.relative_to(repo_root)}:{node.lineno}: chart {node.name!r} lacks metadata for arguments: {', '.join(missing)}")
        required = sum(bool(value["required"]) for value in parsed)
        source_signature = ast.unparse(node.args)
        records.append({
            "name": node.name, "kind": "chart", "signature": signature, "source_signature": source_signature,
            "arity": {"required": required, "optional": len(parsed) - required}, "arguments": arguments,
            "constraints": metadata.get("constraints", []),
            "example": metadata.get("example", f"fig, ax = rkv.{node.name}(data)"),
            "available_in": metadata.get("available_in") or availability_for(),
            "stability": metadata.get("stability", "stable"), "since": metadata.get("since", "1.0.0"),
            "description": metadata.get("description") or (ast.get_docstring(node) or node.name).split("\n", 1)[0],
            "contract_pointer": _pointer("chart", node.name), "docs": _pointer("chart", node.name),
            "source": {"file": str(path.relative_to(repo_root)), "line": node.lineno},
        })
    return records, errors


def _declared_python_primitives(path: Path, repo_root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    text = path.read_text(encoding="utf-8")
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    for start, _, metadata in _metadata_blocks(text, python=True):
        if not metadata.get("name"):
            continue
        name = str(metadata["name"])
        kind = str(metadata.get("kind", "command"))
        try:
            parsed = parse_xparse_signature(str(metadata.get("signature", "")))
        except ContractError as exc:
            errors.append(f"{path.relative_to(repo_root)}:{text.count(chr(10), 0, start) + 1}: {exc}")
            continue
        declared = metadata.get("arguments", [])
        if len(declared) != len(parsed):
            errors.append(f"{path.relative_to(repo_root)}: generated primitive {name!r} argument metadata does not match its signature")
        arguments = []
        for index, syntax in enumerate(parsed):
            value = declared[index] if index < len(declared) else {}
            arguments.append({
                **syntax, "name": value.get("name", f"argument_{index + 1}"),
                "type": value.get("type", "text"), "description": value.get("description", "Undocumented argument."),
            })
        required = sum(bool(value["required"]) for value in parsed)
        records.append({
            "name": name, "kind": kind, "signature": " ".join(str(metadata.get("signature", "")).split()),
            "source_signature": str(metadata.get("signature", "")),
            "arity": {"required": required, "optional": len(parsed) - required}, "arguments": arguments,
            "constraints": metadata.get("constraints", []), "example": metadata["example"],
            "available_in": metadata.get("available_in") or availability_for(),
            "stability": metadata.get("stability", "stable"), "since": metadata.get("since", "1.0.0"),
            "description": metadata.get("description", name),
            "contract_pointer": _pointer(kind, name), "docs": _pointer(kind, name),
            "source": {"file": str(path.relative_to(repo_root)), "line": text.count("\n", 0, start) + 1},
        })
    return records, errors


def _primitive_files(repo_root: Path) -> list[Path]:
    templates = repo_root / "latex_templates"
    return [
        *sorted(templates.glob("reportkit*.sty")),
        *sorted((templates / "themes").glob("reportkit-theme-*.sty")),
        *sorted((templates / "publication_types").glob("reportkit-*.sty")),
    ]


def _merge_record(
    primitives: dict[str, dict[str, dict[str, Any]]], record: dict[str, Any], errors: list[str],
) -> None:
    bucket = primitives[record["kind"]]
    previous = bucket.get(record["name"])
    if previous:
        if previous["signature"] != record["signature"]:
            errors.append(f"duplicate primitive {record['name']!r} has conflicting signatures")
            return
        for key in ("publication_types", "themes", "renderers"):
            previous["available_in"][key] = sorted(
                set(previous["available_in"][key]) | set(record["available_in"][key])
            )
        return
    bucket[record["name"]] = record


def generate_registry(repo_root: Path | None = None, *, strict: bool = False) -> dict[str, Any]:
    repo_root = (repo_root or Path(__file__).resolve().parents[2]).resolve()
    primitives: dict[str, dict[str, Any]] = {kind: {} for kind in PRIMITIVE_KINDS}
    errors: list[str] = []
    for path in _primitive_files(repo_root):
        records, file_errors = _latex_primitives(path, repo_root)
        errors.extend(file_errors)
        for record in records:
            _merge_record(primitives, record, errors)
    chart_records, chart_errors = _chart_primitives(repo_root / "python_scripts" / "reportkit_viz.py", repo_root)
    errors.extend(chart_errors)
    for record in chart_records:
        _merge_record(primitives, record, errors)
    class_text = (repo_root / "latex_templates" / "reportkit.cls").read_text(encoding="utf-8")
    class_match = re.search(r"\\ProvidesClass\{[^}]+\}\[[^]]+\s+v([^\s]+)", class_text)
    class_version = class_match.group(1) if class_match else "unknown"
    if strict and errors:
        raise ContractError("\n".join(errors))
    return {
        "primitives": primitives, "contract_errors": errors,
        "figures": sorted(primitives["figure"]),
        "callouts": {
            "public": sorted(name for name in primitives["callout"] if name in CALLOUT_ENVIRONMENTS and name not in CALLOUT_ALIASES),
            "aliases": {name: target for name, target in CALLOUT_ALIASES.items() if name in primitives["callout"]},
        },
        "charts": sorted(name for name in primitives["chart"] if name in LEGACY_CHART_NAMES), "commands": dict(COMMANDS),
        "command_contract": COMMAND_CONTRACT, "class_version": class_version,
        "sources": {"primitives": "source-adjacent <reportkit-contract> blocks", "charts": "python_scripts/reportkit_viz.py"},
    }


def skill_inventory(skill_path: Path) -> dict[str, set[str]]:
    """Read historical hand-authored inventories during the v1.x transition."""
    text = skill_path.read_text(encoding="utf-8")
    figures: set[str] = set()
    for line in text.splitlines():
        if "|" in line and "Use" not in line and "---" not in line:
            cells = [cell.strip() for cell in line.split("|")]
            if len(cells) >= 3:
                figures.update(name for name in re.findall(r"`([^`]+)`", cells[2]) if name != "reportkit_viz.py")
    callout_match = re.search(r"Use semantic callouts only when their meaning matters:\s*([^\.]+)", text)
    callouts = set(re.findall(r"`([^`]+)`", callout_match.group(1))) if callout_match else set()
    return {"figures": figures, "callouts": callouts}


def check_skill_drift(repo_root: Path | None = None) -> list[str]:
    """Compatibility wrapper over full generated-document drift checks."""
    repo_root = (repo_root or Path(__file__).resolve().parents[2]).resolve()
    registry = generate_registry(repo_root)
    errors = list(registry["contract_errors"])
    try:
        from .documentation import check_documentation
    except ImportError:
        inventory = skill_inventory(repo_root / "SKILL.md")
        if set(registry["figures"]) != inventory["figures"]:
            errors.append("figure inventory drift")
        if set(registry["callouts"]["public"]) != inventory["callouts"]:
            errors.append("callout inventory drift")
        return errors
    errors.extend(check_documentation(repo_root, registry=registry))
    return errors
