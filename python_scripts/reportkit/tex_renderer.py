"""Safe TeX rendering for the constrained ReportKit authoring IR.

All user-controlled text is escaped here.  The only unescaped input accepted
by this renderer is the contents of a fragment selected with the explicit
``fragment:`` directive field; callers must pass a fragment root and the IR
validator has already confined that path to ``fragments/*.tex``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .authoring_ir import AuthoringIR, AuthoringValidationError, DirectiveNode, _option_values, _primitive_records, validate_ir
from .latex import tex_escape


def _render_options(value: str) -> str:
    options = _option_values(value)
    rendered: list[str] = []
    for key, option_value in options.items():
        safe_key = tex_escape(key)
        if option_value == "":
            rendered.append(safe_key)
        else:
            rendered.append(f"{safe_key}={{{tex_escape(option_value)}}}")
    return ",".join(rendered)


def _argument_text(argument: Mapping[str, Any], supplied: Mapping[str, str]) -> str | None:
    name = str(argument["name"])
    if name not in supplied:
        if argument.get("specifier") == "O":
            default = argument.get("default")
            return "" if default is None else str(default)
        return None
    value = str(supplied[name])
    if argument.get("name") == "options" or argument.get("type") == "options":
        return _render_options(value)
    return tex_escape(value)


def _render_arguments(node: DirectiveNode, record: Mapping[str, Any]) -> str:
    values: list[str] = []
    supplied = dict(node.arguments)
    declared_names = {
        str(argument.get("name"))
        for argument in record.get("arguments", [])
        if isinstance(argument, Mapping) and argument.get("name")
    }
    if {"title", "legacy_suffix"}.issubset(declared_names) and {"title", "legacy_suffix"}.issubset(supplied):
        raise ValueError(
            f"callout {node.primitive!r} cannot set both replacement 'title' and legacy 'legacy_suffix'"
        )
    # Keep the Markdown surface ergonomic while rendering the exact LaTeX
    # options slot expected by the presentation composition.
    if node.primitive == "assertionslide" and "kicker" in supplied and "options" not in supplied:
        supplied["options"] = f"kicker={supplied.pop('kicker')}"
    if node.primitive == "cardgrid" and "columns" in supplied and "options" not in supplied:
        supplied["options"] = f"columns={supplied.pop('columns')}"
    for argument in record.get("arguments", []):
        if not isinstance(argument, Mapping):
            continue
        value = _argument_text(argument, supplied)
        if value is None:
            if argument.get("required"):
                raise ValueError(f"{node.primitive!r} is missing required argument {argument.get('name')!r}")
            continue
        if argument.get("specifier") in {"O", "o"}:
            values.append(f"[{value}]")
        else:
            values.append(f"{{{value}}}")
    return "".join(values)


def _fragment_text(node: DirectiveNode, fragment_root: Path | None) -> str:
    if not node.fragment:
        return ""
    if fragment_root is None:
        raise ValueError("a fragment root is required to render a trusted ReportKit fragment")
    fragment_name = Path(node.fragment)
    if fragment_name.is_absolute() or ".." in fragment_name.parts or fragment_name.parent != Path(".") or not fragment_name.name.endswith(".tex"):
        raise ValueError(f"unsafe trusted fragment {node.fragment!r}")
    path = fragment_root / "fragments" / fragment_name.name
    try:
        path.resolve().relative_to((fragment_root / "fragments").resolve())
    except ValueError as exc:
        raise ValueError(f"unsafe trusted fragment {node.fragment!r}") from exc
    if not path.is_file():
        raise ValueError(f"trusted fragment {node.fragment!r} does not exist in fragments/")
    return path.read_text(encoding="utf-8")


def _body(node: DirectiveNode, fragment_root: Path | None, records: Mapping[str, Mapping[str, Any]]) -> str:
    pieces: list[str] = []
    if node.content:
        pieces.append(tex_escape(node.content))
    trusted = _fragment_text(node, fragment_root)
    if trusted:
        pieces.append(trusted.rstrip("\n"))
    for child in node.children:
        pieces.append(_render_node(child, fragment_root=fragment_root, records=records))
    return "\n".join(piece for piece in pieces if piece)


def _frame_wrapper(record: Mapping[str, Any]) -> tuple[str, str] | None:
    for constraint in record.get("constraints", []):
        if not isinstance(constraint, Mapping) or constraint.get("code") != "content_only_wrap_in_frame":
            continue
        description = str(constraint.get("description", ""))
        return ("[plain]" if "[plain]" in description else "", "")
    return None


def _render_node(node: DirectiveNode, *, fragment_root: Path | None, records: Mapping[str, Mapping[str, Any]]) -> str:
    record = records.get(node.primitive)
    if record is None:
        raise ValueError(f"unknown ReportKit primitive {node.primitive!r}")
    kind = str(record.get("kind", node.kind or "composition"))
    args = _render_arguments(node, record)
    body = _body(node, fragment_root, records)
    if kind == "command":
        result = f"\\{node.primitive}{args}"
        if body:
            result += "\n" + body
    else:
        result = f"\\begin{{{node.primitive}}}{args}"
        if body:
            result += "\n" + body
        result += f"\n\\end{{{node.primitive}}}"
    wrapper = _frame_wrapper(record)
    if wrapper is not None:
        opening = f"\\begin{{frame}}{wrapper[0]}"
        result = f"{opening}\n{result}\n\\end{{frame}}"
    return result


def render_node(node: DirectiveNode, *, fragment_root: Path | None = None, registry: Mapping[str, Any] | None = None) -> str:
    """Render one already-validated directive node to safe TeX."""
    return _render_node(node, fragment_root=fragment_root, records=_primitive_records(registry))


def render_ir(
    ir: AuthoringIR,
    *,
    fragment_root: Path | None = None,
    publication_type: str | None = None,
    theme: str | None = None,
    renderer: str | None = None,
    links: set[str] | None = None,
    registry: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    """Validate and render all directives, keyed by their Pandoc markers."""
    diagnostics = validate_ir(
        ir,
        publication_type=publication_type,
        theme=theme,
        renderer=renderer,
        root=fragment_root,
        links=links,
        registry=registry,
    )
    if diagnostics:
        raise AuthoringValidationError(diagnostics)
    records = _primitive_records(registry)
    result: dict[str, str] = {}
    for node in ir.nodes:
        if node.placeholder:
            result[node.placeholder] = _render_node(node, fragment_root=fragment_root, records=records)
    return result


def render_directives(
    ir: AuthoringIR,
    *,
    fragment_root: Path | None = None,
    publication_type: str | None = None,
    theme: str | None = None,
    renderer: str | None = None,
    links: set[str] | None = None,
) -> dict[str, str]:
    """Compatibility alias for :func:`render_ir`."""
    return render_ir(
        ir,
        fragment_root=fragment_root,
        publication_type=publication_type,
        theme=theme,
        renderer=renderer,
        links=links,
    )
