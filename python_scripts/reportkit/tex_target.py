"""Gates for direct-TeX projects (agent reasoning loop spec §4.3)."""
from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from .config import theme_engine_conflict
from .diagnostics import make_diagnostic
from .publications import required_engine_for
from .target import TargetState


_REQUIRED_OPTIONS = ("publication-type", "theme")


def _without_tex_comments(source: str) -> str:
    """Remove TeX comments while preserving escaped percent signs."""
    lines: list[str] = []
    for line in source.splitlines():
        escaped = False
        end = len(line)
        for index, char in enumerate(line):
            if char == "%" and not escaped:
                end = index
                break
            if char == "\\":
                escaped = not escaped
            else:
                escaped = False
        lines.append(line[:end])
    return "\n".join(lines)


def _read_group(source: str, cursor: int, opening: str, closing: str) -> tuple[str, int] | None:
    """Read one balanced TeX delimiter group beginning at ``cursor``."""
    if cursor >= len(source) or source[cursor] != opening:
        return None
    start = cursor + 1
    depth = 1
    cursor += 1
    while cursor < len(source):
        char = source[cursor]
        if char == "\\":
            cursor += 2
            continue
        if char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return source[start:cursor], cursor + 1
        cursor += 1
    return None


def _split_options(value: str) -> list[str] | None:
    """Split class options on commas outside nested braces."""
    parts: list[str] = []
    start = 0
    depth = 0
    cursor = 0
    while cursor < len(value):
        char = value[cursor]
        if char == "\\":
            cursor += 2
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth < 0:
                return None
        elif char == "," and depth == 0:
            parts.append(value[start:cursor])
            start = cursor + 1
        cursor += 1
    if depth:
        return None
    parts.append(value[start:])
    return parts


def read_class_options(tex: Path) -> dict[str, str] | None:
    """Read target keys from ``\\documentclass[...,]{...}``.

    Options may appear in either order and may be surrounded by other standard
    class options. ``None`` means the declaration is absent, malformed, or
    does not specify both ReportKit target keys.
    """
    try:
        source = _without_tex_comments(Path(tex).read_text(encoding="utf-8"))
    except (OSError, UnicodeError):
        return None

    command = re.compile(r"\\documentclass(?:\*)?(?![A-Za-z@])")
    for match in command.finditer(source):
        cursor = match.end()
        while cursor < len(source) and source[cursor].isspace():
            cursor += 1
        group = _read_group(source, cursor, "[", "]")
        if group is None:
            continue
        raw_options, cursor = group
        while cursor < len(source) and source[cursor].isspace():
            cursor += 1
        class_group = _read_group(source, cursor, "{", "}")
        if class_group is None or class_group[0].strip() not in {"reportkit", "reportkit-slides"}:
            continue

        options: dict[str, str] = {}
        option_parts = _split_options(raw_options)
        if option_parts is None:
            continue
        for option in option_parts:
            key, separator, value = option.partition("=")
            if not separator:
                continue
            key = key.strip()
            value = value.strip()
            if key in _REQUIRED_OPTIONS:
                # Duplicate target keys are ambiguous and must not be treated
                # as an authoritative lock.
                if key in options or not value:
                    options = {}
                    break
                options[key] = value
        if all(key in options for key in _REQUIRED_OPTIONS):
            return options
    return None


def tex_gates(state: TargetState, tex: Path) -> list[dict[str, Any]]:
    """Reject a direct-TeX source whose declared target is absent or differs."""
    options = read_class_options(tex)
    expected = {"publication-type": state.publication_type, "theme": state.theme}
    if options == expected:
        return []

    if options is None:
        message = (
            f"{tex}: \\documentclass options must declare "
            "publication-type and theme to match publication.yaml"
        )
    else:
        differences = [
            f"{key}={options[key]!r} (expected {value!r})"
            for key, value in expected.items()
            if options.get(key) != value
        ]
        message = f"{tex}: direct-TeX target differs from publication.yaml: {', '.join(differences)}"
    return [make_diagnostic(
        "target_contract", message, code="RK_TARGET_MISMATCH",
        source={"file": str(tex)},
        details={"expected": expected, "observed": options},
    )]


def engine_gate(state: TargetState, requested_engine: str | None) -> list[dict[str, Any]]:
    """Block a LuaLaTeX target when its resolved engine was downgraded."""
    engine = str(requested_engine or required_engine_for(state.theme) or "pdflatex")
    required = required_engine_for(state.theme)
    conflict = theme_engine_conflict({"theme": state.theme, "engine": engine})
    if not conflict or required != "lualatex" or engine != "pdflatex":
        return []
    return [make_diagnostic(
        "environment_error", conflict, code="RK_ENGINE_DOWNGRADE",
        details={"theme": state.theme, "required_engine": required, "requested_engine": engine},
    )]
