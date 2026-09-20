"""Stdlib parser for ReportKit's fenced Markdown directive dialect.

Canonical form::

    ```reportkit messageslide
    headline: Revenue is accelerating
    fragment: fig-growth.tex
    ```

The selector can instead be supplied as ``primitive:``, ``name:`` or
``composition:`` in the body.  Values are plain text; a JSON object is also
accepted for machine-generated directives.  Deliberately, there is no raw
TeX field.  A directive can opt into a trusted ``fragment:`` file, which is
validated as a filename under the consumer project's ``fragments/`` folder
and copied into the generated TeX unchanged by :mod:`reportkit.tex_renderer`.

Only fences whose info string starts with ``reportkit`` are consumed.  All
other Markdown is returned unchanged for Pandoc.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import shlex
from typing import Any, Mapping

from .authoring_ir import AuthoringIR, DirectiveNode, SourceLocation
from .diagnostics import make_diagnostic


_FENCE = re.compile(r"^(?P<indent>[ \t]{0,3})(?P<mark>`{3,}|~{3,})(?P<info>[^\n]*)\n?$")
_COLON_FENCE = re.compile(r"^(?P<indent>[ \t]{0,3}):::?[ \t]+(?P<info>[^\n]*)\n?$")
_KEY = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")
_SELECTOR_KEYS = ("primitive", "name", "composition", "directive")
_ESCAPE_KEYS = {"fragment", "trusted_fragment"}
_PLACEHOLDER_PREFIX = "REPORTKITDIRECTIVE"


@dataclass(frozen=True)
class ParsedMarkdown:
    """The Pandoc input and directives extracted from one manuscript."""

    ir: AuthoringIR
    placeholders: Mapping[str, DirectiveNode]
    diagnostics: tuple[dict[str, Any], ...] = ()

    @property
    def markdown(self) -> str:
        return self.ir.markdown

    @property
    def directives(self) -> tuple[DirectiveNode, ...]:
        return self.ir.nodes

    def as_dict(self) -> dict[str, Any]:
        return {
            **self.ir.as_dict(),
            "diagnostics": list(self.diagnostics),
            "placeholders": sorted(self.placeholders),
        }


def _clean_value(value: Any) -> str:
    if isinstance(value, str):
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            return value[1:-1]
        return value
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _line_diagnostic(file: str, line: int, message: str, *, rule: str, details: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return make_diagnostic(
        "publication_validation",
        message,
        code=f"RK_AUTHORING_{rule.upper()}",
        source={"file": file, "line": line, "line_end": line},
        details=details,
    )


def _is_reportkit_info(info: str) -> tuple[bool, str | None]:
    value = info.strip()
    if not value:
        return False, None
    try:
        tokens = shlex.split(value)
    except ValueError:
        tokens = value.split()
    if not tokens:
        return False, None
    first = tokens[0]
    if first == "reportkit":
        return True, tokens[1] if len(tokens) > 1 else None
    for prefix in ("reportkit:", "reportkit::", "reportkit/"):
        if first.startswith(prefix):
            return True, first[len(prefix):] or (tokens[1] if len(tokens) > 1 else None)
    return False, None


def _parse_inline_selector(selector: str | None) -> tuple[str | None, dict[str, str]]:
    if not selector:
        return None, {}
    selector = selector.strip()
    if not selector:
        return None, {}
    try:
        tokens = shlex.split(selector)
    except ValueError:
        tokens = selector.split()
    if not tokens:
        return None, {}
    name = tokens[0]
    arguments: dict[str, str] = {}
    for token in tokens[1:]:
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        if _KEY.fullmatch(key):
            arguments[key] = _clean_value(value)
    return name, arguments


def _parse_body(
    body_lines: list[str],
    selector: str | None,
    *,
    source_file: str,
    start_line: int,
) -> tuple[str | None, dict[str, str], str, str | None, list[dict[str, Any]]]:
    """Parse the key/value portion of one directive fence."""
    diagnostics: list[dict[str, Any]] = []
    primitive, arguments = _parse_inline_selector(selector)
    values: dict[str, Any] = {}
    content_lines: list[str] = []
    nonblank = [line for line in body_lines if line.strip()]
    if len(nonblank) == 1 and nonblank[0].lstrip().startswith("{"):
        try:
            decoded = json.loads(nonblank[0])
        except json.JSONDecodeError as exc:
            diagnostics.append(_line_diagnostic(source_file, start_line, f"invalid ReportKit directive JSON: {exc.msg}", rule="directive_syntax"))
        else:
            if not isinstance(decoded, dict):
                diagnostics.append(_line_diagnostic(source_file, start_line, "ReportKit directive JSON must be an object", rule="directive_syntax"))
            else:
                values.update(decoded)
    else:
        index = 0
        while index < len(body_lines):
            raw = body_lines[index]
            stripped = raw.strip()
            if not stripped:
                index += 1
                continue
            if stripped.startswith("#"):
                index += 1
                continue
            if ":" in raw:
                key, value = raw.split(":", 1)
                key = key.strip()
                if _KEY.fullmatch(key):
                    value = value.strip()
                    if value == "|":
                        index += 1
                        multiline: list[str] = []
                        while index < len(body_lines):
                            multiline.append(body_lines[index][2:] if body_lines[index].startswith("  ") else body_lines[index])
                            index += 1
                        values[key] = "\n".join(multiline).rstrip("\n")
                        continue
                    values[key] = _clean_value(value)
                    index += 1
                    continue
            if "=" in raw:
                key, value = raw.split("=", 1)
                key = key.strip()
                if _KEY.fullmatch(key):
                    values[key] = _clean_value(value)
                    index += 1
                    continue
            if primitive is None and not values and len(content_lines) == 0:
                primitive = stripped
            else:
                content_lines.append(raw)
            index += 1

    for key, value in values.items():
        key = str(key)
        if key in _SELECTOR_KEYS:
            candidate = _clean_value(value)
            if primitive is not None and primitive != candidate:
                diagnostics.append(_line_diagnostic(
                    source_file,
                    start_line,
                    f"directive selectors disagree: {primitive!r} and {candidate!r}",
                    rule="directive_selector",
                    details={"selectors": [primitive, candidate]},
                ))
            primitive = candidate
        elif key in {"args", "arguments"}:
            if isinstance(value, dict):
                arguments.update({str(k): _clean_value(v) for k, v in value.items()})
            else:
                try:
                    decoded = json.loads(str(value))
                except json.JSONDecodeError:
                    diagnostics.append(_line_diagnostic(source_file, start_line, f"directive {key} must be a JSON object", rule="directive_syntax"))
                else:
                    if isinstance(decoded, dict):
                        arguments.update({str(k): _clean_value(v) for k, v in decoded.items()})
                    else:
                        diagnostics.append(_line_diagnostic(source_file, start_line, f"directive {key} must be a JSON object", rule="directive_syntax"))
        elif key == "content":
            content_lines = [_clean_value(value)]
        elif key in _ESCAPE_KEYS:
            # Handled separately below; keep it out of primitive arguments.
            continue
        elif key in {"kind", "frame", "children"}:
            continue
        else:
            arguments[key] = _clean_value(value)
    fragment = None
    for key in _ESCAPE_KEYS:
        if key in values:
            fragment = _clean_value(values[key])
            break
    content = "\n".join(content_lines).strip("\n")
    return primitive, arguments, content, fragment, diagnostics


def _normalize_fragment(fragment: str | None) -> str | None:
    if not fragment:
        return None
    value = fragment.strip()
    if value.startswith("fragments/"):
        value = value.removeprefix("fragments/")
    if not value.endswith(".tex"):
        value += ".tex"
    return value


def parse_markdown(text: str, *, source_file: str | Path = "<memory>") -> ParsedMarkdown:
    """Parse ReportKit fences and return Markdown ready for Pandoc.

    The parser is line-oriented on purpose: source line numbers remain exact,
    and ordinary Markdown never passes through a second parser.  A malformed
    ReportKit fence is replaced by a placeholder too, allowing validation to
    report all other directives in the same source in one pass.
    """
    filename = str(source_file)
    lines = text.splitlines(keepends=True)
    output: list[str] = []
    nodes: list[DirectiveNode] = []
    placeholders: dict[str, DirectiveNode] = {}
    diagnostics: list[dict[str, Any]] = []
    index = 0
    directive_index = 0
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:10].upper()

    while index < len(lines):
        match = _FENCE.match(lines[index])
        colon_match = _COLON_FENCE.match(lines[index]) if not match else None
        active = match or colon_match
        if active:
            info = active.group("info").strip()
            is_reportkit, selector = _is_reportkit_info(info)
            if is_reportkit:
                marker = active.group("mark") if match else ":::"
                if match:
                    mark_char = marker[0]
                    close = re.compile(rf"^[ \t]{{0,3}}{re.escape(mark_char)}{{{len(marker)},}}[ \t]*\n?$")
                else:
                    close = re.compile(r"^[ \t]{0,3}:::[ \t]*\n?$")
                body_start = index + 1
                end = body_start
                while end < len(lines) and not close.match(lines[end]):
                    end += 1
                if end == len(lines):
                    diagnostics.append(_line_diagnostic(
                        filename,
                        index + 1,
                        "unterminated ReportKit directive fence",
                        rule="directive_fence",
                    ))
                    body_end = len(lines)
                    next_index = len(lines)
                else:
                    body_end = end
                    next_index = end + 1
                primitive, arguments, content, fragment, parse_errors = _parse_body(
                    [line.rstrip("\n") for line in lines[body_start:body_end]],
                    selector,
                    source_file=filename,
                    start_line=index + 1,
                )
                diagnostics.extend(parse_errors)
                primitive = primitive or ""
                kind = None
                # Keep the parse result typed even when validation will report
                # the missing selector; this lets later directives validate.
                if not primitive:
                    diagnostics.append(_line_diagnostic(
                        filename,
                        index + 1,
                        "ReportKit directive is missing a primitive selector",
                        rule="missing_primitive",
                    ))
                if "kind" in arguments:
                    kind = arguments.pop("kind")
                source = SourceLocation(filename, index + 1, next_index)
                placeholder = f"{_PLACEHOLDER_PREFIX}{digest}{directive_index:04d}"
                node = DirectiveNode(
                    primitive=primitive,
                    arguments=arguments,
                    content=content,
                    fragment=_normalize_fragment(fragment),
                    source=source,
                    placeholder=placeholder,
                    kind=kind,
                )
                nodes.append(node)
                placeholders[placeholder] = node
                output.extend([placeholder + "\n", "\n"])
                directive_index += 1
                index = next_index
                continue
        output.append(lines[index])
        index += 1

    return ParsedMarkdown(
        ir=AuthoringIR(
            source=text,
            source_file=filename,
            markdown="".join(output),
            nodes=tuple(nodes),
        ),
        placeholders=placeholders,
        diagnostics=tuple(diagnostics),
    )


def parse_directives(text: str, *, source_file: str | Path = "<memory>") -> ParsedMarkdown:
    """Compatibility alias for callers interested only in directive parsing."""
    return parse_markdown(text, source_file=source_file)


def replace_placeholders(text: str, replacements: Mapping[str, str]) -> str:
    """Replace parser markers in Pandoc output without interpreting TeX."""
    result = text
    for marker, replacement in replacements.items():
        result = result.replace(marker, replacement)
    return result


def directive_source_files(root: Path) -> list[Path]:
    """Return manuscript files that may contain directives, in stable order."""
    manuscript = root / "manuscript"
    order = manuscript / "order.txt"
    if order.is_file():
        result: list[Path] = []
        for raw in order.read_text(encoding="utf-8").splitlines():
            value = raw.strip()
            if value and not value.startswith("#") and (manuscript / value).is_file() and value.endswith(".md"):
                result.append(manuscript / value)
        return result
    return sorted(manuscript.rglob("*.md")) if manuscript.is_dir() else []
