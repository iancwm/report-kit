"""Typed intermediate representation for constrained ReportKit authoring.

The IR is deliberately small.  Markdown remains the author's surface and
Pandoc remains responsible for ordinary Markdown; this module only describes
the fenced ``reportkit`` blocks that are safe to expand into ReportKit TeX.

The IR is also the boundary at which primitive usage is checked.  In
particular, no TeX or Pandoc process belongs in this module.  A trusted
fragment is represented as a path, rather than as an arbitrary TeX field, so
the escape hatch stays visible in both validation and generated maps.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping
import re

from .diagnostics import make_diagnostic, suggest
from .registry import generate_registry


AUTHORING_SCHEMA_VERSION = "1.0.0"
_RESERVED_FIELDS = {
    "primitive", "name", "composition", "kind", "content", "fragment",
    "trusted_fragment", "children", "frame", "args", "arguments",
}
_FORBIDDEN_RAW_FIELDS = {"raw", "raw_tex", "latex", "tex"}
_SAFE_FRAGMENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*\.tex\Z")


@dataclass(frozen=True)
class SourceLocation:
    """A location in the author's Markdown source."""

    file: str
    line: int
    line_end: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "file": self.file,
            "line": self.line,
            "line_end": self.line_end if self.line_end is not None else self.line,
        }


@dataclass(frozen=True)
class DirectiveNode:
    """One normalized ReportKit directive.

    ``arguments`` contains only primitive arguments.  The parser removes the
    directive selector and escape-hatch fields before constructing the node.
    ``fragment`` is a publication-root-relative trusted fragment name and is
    never interpreted as TeX source by the parser or validator.
    """

    primitive: str
    arguments: Mapping[str, str] = field(default_factory=dict)
    content: str = ""
    fragment: str | None = None
    source: SourceLocation = field(default_factory=lambda: SourceLocation("<memory>", 1, 1))
    children: tuple["DirectiveNode", ...] = ()
    placeholder: str | None = None
    kind: str | None = None

    @property
    def name(self) -> str:
        """Compatibility spelling used by callers that call these directives nodes."""
        return self.primitive

    @property
    def args(self) -> Mapping[str, str]:
        return self.arguments

    def as_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "type": "directive",
            "primitive": self.primitive,
            "kind": self.kind,
            "arguments": dict(self.arguments),
            "content": self.content,
            "fragment": self.fragment,
            "source": self.source.as_dict(),
            "children": [child.as_dict() for child in self.children],
        }
        if self.placeholder is not None:
            value["placeholder"] = self.placeholder
        return value


@dataclass(frozen=True)
class AuthoringIR:
    """A parsed Markdown document and its directive nodes."""

    source: str
    source_file: str
    markdown: str
    nodes: tuple[DirectiveNode, ...] = ()

    @property
    def directives(self) -> tuple[DirectiveNode, ...]:
        return self.nodes

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": AUTHORING_SCHEMA_VERSION,
            "source": self.source,
            "source_file": self.source_file,
            "nodes": [node.as_dict() for node in self.nodes],
        }


class AuthoringValidationError(ValueError):
    """Raised by the renderer when a caller skipped the validation step."""

    def __init__(self, diagnostics: Iterable[dict[str, Any]]) -> None:
        self.diagnostics = list(diagnostics)
        message = "; ".join(item["message"] for item in self.diagnostics)
        super().__init__(message or "invalid ReportKit authoring")


def _diagnostic(
    rule: str,
    message: str,
    node: DirectiveNode,
    *,
    primitive: str | None = None,
    candidates: Iterable[str] = (),
    details: Mapping[str, Any] | None = None,
    kind: str = "publication_validation",
) -> dict[str, Any]:
    details_value = {"contract_pointer": f"#/capabilities/primitives/{node.kind or 'composition'}/{primitive or node.primitive}"}
    details_value.update(details or {})
    return make_diagnostic(
        kind,
        message,
        code=f"RK_AUTHORING_{rule.upper()}",
        primitive=primitive or node.primitive,
        source=node.source.as_dict(),
        candidates=candidates,
        details=details_value,
    )


def _primitive_records(registry: Mapping[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    data = registry if registry is not None else generate_registry()
    result: dict[str, dict[str, Any]] = {}
    for kind, records in data.get("primitives", {}).items():
        for name, record in records.items():
            # The current catalog has unique names across kinds.  Preserve the
            # first record if a future extension introduces an ambiguous name;
            # an explicit ``kind`` still selects the record below.
            result.setdefault(str(name), {**record, "kind": kind})
    return result


def _lookup_record(
    node: DirectiveNode,
    records: Mapping[str, Mapping[str, Any]],
) -> tuple[Mapping[str, Any] | None, list[dict[str, Any]]]:
    record = records.get(node.primitive)
    if record is None:
        return None, [_diagnostic(
            "unknown_primitive",
            f"unknown ReportKit primitive {node.primitive!r}; choose a supported primitive",
            node,
            candidates=suggest(node.primitive, records),
        )]
    if node.kind and node.kind != record.get("kind"):
        return None, [_diagnostic(
            "primitive_kind",
            f"primitive {node.primitive!r} is a {record.get('kind')} primitive, not {node.kind!r}",
            node,
            candidates=[str(record.get("kind"))],
            details={"expected": record.get("kind"), "supplied": node.kind},
        )]
    return record, []


def _availability_errors(
    node: DirectiveNode,
    record: Mapping[str, Any],
    *,
    publication_type: str | None,
    theme: str | None,
    renderer: str | None,
) -> list[dict[str, Any]]:
    available = record.get("available_in") or {}
    errors: list[dict[str, Any]] = []
    checks = (
        ("publication_type", publication_type, available.get("publication_types", [])),
        ("theme", theme, available.get("themes", [])),
        ("renderer", renderer, available.get("renderers", [])),
    )
    failed = [
        (label, supplied, choices)
        for label, supplied, choices in checks
        if supplied is not None and supplied not in choices
    ]
    if failed:
        labels = ", ".join(f"{label} {supplied!r}" for label, supplied, _ in failed)
        candidates = sorted({str(item) for _, _, choices in failed for item in choices})
        errors.append(_diagnostic(
            "unavailable_primitive",
            f"primitive {node.primitive!r} is not available for {labels}",
            node,
            candidates=candidates,
            details={
                "availability": {
                    label: {"supplied": supplied, "available": list(choices)}
                    for label, supplied, choices in failed
                },
            },
        ))
    return errors


def _option_values(value: str) -> dict[str, str]:
    """Parse the deliberately small, non-TeX options notation.

    Directive options are ``key=value,key=value``.  Braces and backslashes
    are rejected here rather than being passed through as an accidental raw
    TeX channel.  The TeX renderer escapes each value independently.
    """
    result: dict[str, str] = {}
    if not value.strip():
        return result
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        if "=" not in item:
            result[item] = ""
            continue
        key, raw_value = item.split("=", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", key):
            result[key] = raw_value.strip("\"'")
    return result


def _numeric_constraint_errors(node: DirectiveNode, record: Mapping[str, Any]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    options = _option_values(node.arguments.get("options", ""))
    values = {**node.arguments, **options}
    for constraint in record.get("constraints", []):
        if not isinstance(constraint, Mapping):
            continue
        if "min" not in constraint and "max" not in constraint:
            continue
        key_candidates = {
            "normalized_point": ("x", "y"),
            "pillar_count": ("count", "pillar_count", "columns"),
            "stage_count": ("count", "stage_count", "stages"),
            "slice_count": ("count", "slice_count", "slices"),
            "max_tasks": ("count", "task_count", "tasks"),
        }.get(str(constraint.get("code")), ("count",))
        supplied_key = next((key for key in key_candidates if key in values), None)
        if supplied_key is None:
            continue
        try:
            number = float(values[supplied_key])
        except (TypeError, ValueError):
            errors.append(_diagnostic(
                "constraint_value",
                f"constraint {constraint.get('code')!r} for {node.primitive!r} needs a numeric value; supplied {values[supplied_key]!r}",
                node,
                details={"constraint": dict(constraint), "supplied": values[supplied_key]},
            ))
            continue
        minimum = constraint.get("min")
        maximum = constraint.get("max")
        if minimum is not None and number < float(minimum) or maximum is not None and number > float(maximum):
            bounds = f"{minimum}..{maximum}" if minimum is not None and maximum is not None else str(minimum or maximum)
            errors.append(_diagnostic(
                "constraint_value",
                f"constraint {constraint.get('code')!r} for {node.primitive!r} expects {bounds}; supplied {values[supplied_key]!r}",
                node,
                details={"constraint": dict(constraint), "expected": {"min": minimum, "max": maximum}, "supplied": values[supplied_key]},
            ))
    return errors


def _validate_node(
    node: DirectiveNode,
    records: Mapping[str, Mapping[str, Any]],
    *,
    publication_type: str | None,
    theme: str | None,
    renderer: str | None,
    root: Path | None,
    links: set[str] | None,
    parent: str | None,
    seen: set[int],
) -> list[dict[str, Any]]:
    # A node can be shared by a caller constructing IR manually.  Avoid
    # repeating diagnostics while still traversing ordinary parsed trees.
    marker = id(node)
    if marker in seen:
        return []
    seen.add(marker)
    record, errors = _lookup_record(node, records)
    if record is None:
        return errors + [
            item for child in node.children for item in _validate_node(
                child, records, publication_type=publication_type, theme=theme,
                renderer=renderer, root=root, links=links, parent=node.primitive, seen=seen,
            )
        ]
    errors.extend(_availability_errors(
        node, record, publication_type=publication_type, theme=theme, renderer=renderer,
    ))
    arguments = {str(item["name"]): item for item in record.get("arguments", []) if isinstance(item, Mapping) and item.get("name")}
    supplied = {key: value for key, value in node.arguments.items() if key not in _RESERVED_FIELDS}
    missing = [
        name for name, argument in arguments.items()
        if argument.get("required") and name not in supplied
    ]
    forbidden = sorted(set(supplied) & _FORBIDDEN_RAW_FIELDS)
    if forbidden:
        errors.append(_diagnostic(
            "raw_tex_forbidden",
            f"directive {node.primitive!r} cannot supply raw TeX field(s) {forbidden}; use an explicit trusted fragment instead",
            node,
            kind="security_violation",
            details={"fields": forbidden},
        ))
    unknown = sorted(set(supplied) - set(arguments) - _FORBIDDEN_RAW_FIELDS)
    if missing:
        errors.append(_diagnostic(
            "missing_arguments",
            f"primitive {node.primitive!r} expects arguments {sorted(arguments)}; missing {missing}",
            node,
            details={"expected": sorted(arguments), "supplied": sorted(supplied), "missing": missing},
        ))
    if unknown:
        errors.append(_diagnostic(
            "unknown_argument",
            f"primitive {node.primitive!r} does not accept argument(s) {unknown}; expected {sorted(arguments)}",
            node,
            details={"expected": sorted(arguments), "supplied": sorted(supplied), "unknown": unknown},
        ))
    if node.fragment and root is not None:
        fragment = Path(node.fragment)
        valid_name = (
            not fragment.is_absolute()
            and ".." not in fragment.parts
            and fragment.parent == Path(".")
            and bool(_SAFE_FRAGMENT.fullmatch(fragment.name))
        )
        if not valid_name:
            errors.append(_diagnostic(
                "unsafe_fragment",
                f"trusted fragment {node.fragment!r} must be a .tex file name inside fragments/",
                node,
                kind="security_violation",
                details={"fragment": node.fragment},
            ))
        else:
            fragment_path = root / "fragments" / fragment.name
            if not fragment_path.is_file():
                errors.append(_diagnostic(
                    "missing_fragment",
                    f"trusted fragment {node.fragment!r} does not exist in fragments/",
                    node,
                    details={"fragment": node.fragment},
                ))
    elif node.fragment:
        fragment = Path(node.fragment)
        if fragment.is_absolute() or ".." in fragment.parts or not _SAFE_FRAGMENT.fullmatch(fragment.name):
            errors.append(_diagnostic(
                "unsafe_fragment",
                f"trusted fragment {node.fragment!r} must be a .tex file name inside fragments/",
                node,
                kind="security_violation",
                details={"fragment": node.fragment},
            ))
    for constraint in record.get("constraints", []):
        if not isinstance(constraint, Mapping):
            continue
        code = str(constraint.get("code", ""))
        if code == "requires_parent_environment" and parent != constraint.get("value"):
            errors.append(_diagnostic(
                "constraint_parent",
                f"primitive {node.primitive!r} is only valid inside {constraint.get('value')!r}; supplied parent {parent!r}",
                node,
                details={"constraint": dict(constraint), "expected_parent": constraint.get("value"), "supplied_parent": parent},
            ))
        if code == "inside_algorithmblock" and parent != "algorithmblock":
            errors.append(_diagnostic(
                "constraint_parent",
                f"primitive {node.primitive!r} is only valid inside 'algorithmblock'; supplied parent {parent!r}",
                node,
                details={"constraint": dict(constraint), "expected_parent": "algorithmblock", "supplied_parent": parent},
            ))
        if code == "known_link" and links is not None:
            key_name = next((name for name in arguments if name in supplied), None)
            if key_name and supplied[key_name] not in links:
                errors.append(_diagnostic(
                    "unknown_link",
                    f"primitive {node.primitive!r} references unknown link key {supplied[key_name]!r}",
                    node,
                    candidates=suggest(supplied[key_name], links),
                    details={"constraint": dict(constraint), "supplied": supplied[key_name]},
                ))
    errors.extend(_numeric_constraint_errors(node, record))
    exact = next((str(item.get("code")) for item in record.get("constraints", []) if isinstance(item, Mapping) and str(item.get("code", "")).startswith("exactly_")), None)
    if exact:
        expected = {"exactly_two_columns": 2, "exactly_three_columns": 3}.get(exact)
        if expected is None:
            expected = 0
        expected_child = "comparisoncolumn" if expected == 2 else "threepartcolumn"
        children = [child for child in node.children if child.primitive == expected_child]
        if len(children) != expected:
            errors.append(_diagnostic(
                "constraint_children",
                f"primitive {node.primitive!r} expects exactly {expected} {expected_child} directives; supplied {len(children)}",
                node,
                details={"constraint": exact, "expected": expected, "supplied": len(children)},
            ))
    for child in node.children:
        errors.extend(_validate_node(
            child, records, publication_type=publication_type, theme=theme,
            renderer=renderer, root=root, links=links, parent=node.primitive, seen=seen,
        ))
    return errors


def validate_ir(
    ir: AuthoringIR,
    *,
    publication_type: str | None = None,
    theme: str | None = None,
    renderer: str | None = None,
    root: Path | None = None,
    links: Iterable[str] | None = None,
    registry: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Validate a parsed IR against the generated primitive contract.

    This is intentionally a pure, one-pass validation API.  It reads the
    local trusted fragment only to check its existence and never invokes an
    external command.
    """
    records = _primitive_records(registry)
    link_set = set(links) if links is not None else None
    errors: list[dict[str, Any]] = []
    seen: set[int] = set()
    for node in ir.nodes:
        errors.extend(_validate_node(
            node, records, publication_type=publication_type, theme=theme,
            renderer=renderer, root=root, links=link_set, parent=None, seen=seen,
        ))
    return errors


def flatten_nodes(ir: AuthoringIR) -> tuple[DirectiveNode, ...]:
    """Return nodes in source order, including manually nested children."""
    result: list[DirectiveNode] = []

    def visit(node: DirectiveNode) -> None:
        result.append(node)
        for child in node.children:
            visit(child)

    for node in ir.nodes:
        visit(node)
    return tuple(result)
